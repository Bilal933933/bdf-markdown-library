"""Conversion worker — runs the pipeline for one queued conversion.

Entry for RQ is `process_conversion_job` (id only; builds its own Session).
`process_conversion` takes explicit deps and is fully testable without Redis.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pymupdf
from PIL import Image
from rq import Queue
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors.codes import ErrorCode
from app.core.errors.exceptions import ConflictError, NotFoundError, ValidationError
from app.domains.conversion.extract import extract_docx, extract_text, split_paragraphs
from app.domains.conversion.models import (
    Asset,
    Block,
    BlockSource,
    BlockType,
    Conversion,
    ConversionStatus,
    Document,
    DocumentMetadata,
    ExtractionInfo,
    ExtractionMethod,
    ImagePayload,
    Page,
    ParagraphPayload,
)
from app.domains.conversion.ocr.select import ocr_page_text
from app.domains.conversion.pipeline.hierarchy import normalize_heading_levels
from app.domains.conversion.pipeline.segment import segment_document
from app.domains.conversion.pipeline.structure import detect_blocks
from app.domains.conversion.quality import QualityDecision, analyze_page
from app.domains.conversion.rendering import build_unit_outputs, collect_stats, render_document
from app.domains.conversion.services.conversions import conversion_from_row
from app.infrastructure.database.tables import ConversionRow, PageCheckpointRow
from app.infrastructure.redis import get_redis
from app.infrastructure.storage import LocalStorage, Storage

logger = logging.getLogger(__name__)

QUEUE_NAME = "conversions"
_JOB_PATH = "app.domains.conversion.pipeline.process.process_conversion_job"
MAX_ATTEMPTS = 3
LEASE_SECONDS = 300


def _row_to_domain(row: ConversionRow) -> Conversion:
    return conversion_from_row(row)


def _beat(row: ConversionRow) -> None:
    row.heartbeat_at = datetime.now(UTC)


def _to_png(data: bytes) -> bytes:
    with Image.open(BytesIO(data)) as image:
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        return buffer.getvalue()


def _extract_assets(
    pdf: pymupdf.Document,
    page_number: int,
    page: Page,
    conversion_id: str,
    storage: Storage,
) -> list[Asset]:
    """Save embedded images referenced by the page and describe them (text path only)."""
    infos = pdf[page_number - 1].get_images(full=True)
    assets: list[Asset] = []
    for block in page.blocks:
        if not isinstance(block.payload, ImagePayload):
            continue
        try:
            index = int(block.payload.asset_id.rsplit("-img", 1)[1])
            pixmap = pymupdf.Pixmap(pdf, infos[index][0])
        except Exception:
            logger.warning("skipping unreadable image %s", block.payload.asset_id)
            continue
        if pixmap.n > 4 or pixmap.alpha:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
        key = f"{conversion_id}/output/assets/{block.payload.asset_id}.png"
        storage.save(key, pixmap.tobytes("png"))
        assets.append(
            Asset(
                id=block.payload.asset_id,
                storage_key=key,
                mime="image/png",
                width=float(pixmap.width),
                height=float(pixmap.height),
                pages=[page_number],
            )
        )
    return assets


def _accepted(page: Page, method: ExtractionMethod) -> bool:
    result = analyze_page(page)
    if result.decision == QualityDecision.ACCEPT:
        page.quality = result.score
        page.extraction_method = method
        return True
    return False


def _ocr_blocks_page(
    text: str, page_number: int, source_file: str, method: ExtractionMethod
) -> Page:
    blocks = [
        Block(
            id=f"p{page_number}-b{order}",
            type=BlockType.PARAGRAPH,
            order=order,
            source=BlockSource(file=source_file, pages=[page_number], method=method),
            payload=ParagraphPayload(text=chunk),
        )
        for order, chunk in enumerate(split_paragraphs(text))
    ]
    return Page(number=page_number, blocks=blocks)


def _process_page(
    pdf: pymupdf.Document,
    page_number: int,
    source_file: str,
    pdf_bytes: bytes,
    settings: Settings,
) -> tuple[Page, bool]:
    """Text first, then OCR of the rendered page; returns (page, accepted)."""
    image: bytes | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            if attempt == 0:
                blocks = detect_blocks(pdf[page_number - 1], pdf_bytes, source_file=source_file)
                page = Page(number=page_number, blocks=blocks)
                if _accepted(page, ExtractionMethod.PYMUPDF):
                    return page, True
            else:
                if image is None:
                    pixmap = pdf[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2))
                    image = pixmap.tobytes("jpg")
                ocr = ocr_page_text(image, "image/jpeg", page_number, settings)
                page = _ocr_blocks_page(ocr.text, page_number, source_file, ocr.method)
                if _accepted(page, ocr.method):
                    return page, True
        except Exception:
            logger.exception("page %d attempt %d failed", page_number, attempt + 1)
    return Page(number=page_number), False


def process_conversion(
    conversion_id: str, db: Session, storage: Storage, settings: Settings | None = None
) -> Conversion:
    """Run extract → quality → render for one conversion; resume-aware."""
    resolved = settings or get_settings()
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    if row.status == ConversionStatus.COMPLETED.value:
        return _row_to_domain(row)
    if row.status in (ConversionStatus.FAILED.value, ConversionStatus.PARTIAL.value):
        raise ConflictError(f"Conversion {conversion_id} is {row.status}; re-queue it first")
    row.status = ConversionStatus.PROCESSING.value
    _beat(row)
    db.commit()

    ext = f".{row.source_file.lower().rsplit('.', 1)[-1]}" if "." in row.source_file else ""
    data = storage.load(f"{conversion_id}/input{ext}")
    failed: list[int] = []
    qualities: list[float] = []
    all_assets: list[Asset] = []
    done = 0
    static_blocks: list[Block] | None = None
    if ext in (".docx", ".txt"):
        try:
            static_blocks = (
                extract_docx(data, row.source_file)
                if ext == ".docx"
                else extract_text(data, row.source_file)
            )
        except ValidationError as exc:
            row.status = ConversionStatus.FAILED.value
            row.error_code = exc.code
            row.error_message = exc.message
            db.commit()
            return _row_to_domain(row)
    static_method = ExtractionMethod.DOCX if ext == ".docx" else ExtractionMethod.TEXT
    pdf_doc: pymupdf.Document | None = None
    if ext == ".pdf":
        pdf_doc = pymupdf.open(stream=data, filetype="pdf")
    elif ext in (".png", ".jpg", ".jpeg", ".webp"):
        try:
            pdf_doc = pymupdf.open(stream=_to_png(data) if ext == ".webp" else data)
        except Exception as exc:
            row.status = ConversionStatus.FAILED.value
            row.error_code = ErrorCode.APP_ERROR
            row.error_message = f"unreadable image: {exc}"
            db.commit()
            return _row_to_domain(row)
    try:
        for page_number in range(1, row.total_pages + 1):
            checkpoint = db.get(
                PageCheckpointRow, {"conversion_id": conversion_id, "page_number": page_number}
            )
            if checkpoint is None:
                checkpoint = PageCheckpointRow(conversion_id=conversion_id, page_number=page_number)
                db.add(checkpoint)
            if checkpoint.status == "done":
                done += 1
                if checkpoint.quality is not None:
                    qualities.append(checkpoint.quality)
                if pdf_doc is not None:
                    saved = Page.model_validate_json(
                        storage.load(f"{conversion_id}/pages/{page_number}.json")
                    )
                    all_assets.extend(
                        _extract_assets(pdf_doc, page_number, saved, conversion_id, storage)
                    )
                continue
            if pdf_doc is not None:
                page, accepted = _process_page(
                    pdf_doc, page_number, row.source_file, data, resolved
                )
            else:
                page = Page(number=page_number, blocks=static_blocks or [])
                accepted = _accepted(page, static_method)
            if (
                accepted
                and page.extraction_method == ExtractionMethod.PYMUPDF
                and pdf_doc is not None
            ):
                all_assets.extend(
                    _extract_assets(pdf_doc, page_number, page, conversion_id, storage)
                )
            storage.save(
                f"{conversion_id}/pages/{page_number}.json", page.model_dump_json().encode()
            )
            checkpoint.attempts = MAX_ATTEMPTS
            if accepted:
                checkpoint.status = "done"
                checkpoint.method = (page.extraction_method or ExtractionMethod.PYMUPDF).value
                checkpoint.quality = page.quality
                qualities.append(page.quality or 0.0)
                done += 1
            else:
                checkpoint.status = "failed"
                failed.append(page_number)
            row.current_page = page_number
            row.progress = round(100 * done / row.total_pages) if row.total_pages else 0
            _beat(row)
            db.commit()
    finally:
        if pdf_doc is not None:
            pdf_doc.close()

    if failed and done == 0:
        row.status = ConversionStatus.FAILED.value
        row.error_code = ErrorCode.PAGE_FAILED
        row.error_message = f"pages failed quality: {failed}"
        db.commit()
        return _row_to_domain(row)

    done_numbers = sorted(
        cp.page_number
        for cp in db.query(PageCheckpointRow)
        .filter_by(conversion_id=conversion_id, status="done")
        .all()
    )
    pages = [
        Page.model_validate_json(storage.load(f"{conversion_id}/pages/{n}.json"))
        for n in done_numbers
    ]
    if failed:
        row.status = ConversionStatus.PARTIAL.value
        row.error_code = ErrorCode.PAGE_FAILED
        row.error_message = f"pages failed quality: {failed}"
    doc = normalize_heading_levels(
        Document(id=conversion_id, source_file=row.source_file, pages=pages, assets=all_assets)
    )
    doc = segment_document(doc)
    used_methods = {block.source.method for page in doc.pages for block in page.blocks}
    ocr_pages = sorted(
        {
            page.number
            for page in doc.pages
            for block in page.blocks
            if block.source.method != ExtractionMethod.PYMUPDF
        }
    )
    doc.metadata = DocumentMetadata(
        page_count=len(pages),
        stats=collect_stats(doc),
        extraction=ExtractionInfo(
            methods=sorted(used_methods, key=lambda m: m.value) or [ExtractionMethod.PYMUPDF],
            ocr_pages=ocr_pages,
            quality=round(sum(qualities) / len(qualities), 3) if qualities else None,
        ),
    )
    assets_by_id = {asset.id: asset.storage_key for asset in doc.assets}
    storage.save(
        f"{conversion_id}/output/document.md", render_document(doc, assets_by_id).encode("utf-8")
    )
    storage.save(
        f"{conversion_id}/output/metadata.json", doc.metadata.model_dump_json(indent=2).encode()
    )
    storage.save(
        f"{conversion_id}/output/assets.json",
        json.dumps(
            [asset.model_dump(mode="json") for asset in doc.assets],
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )
    for key, content in build_unit_outputs(doc, assets_by_id).items():
        storage.save(f"{conversion_id}/output/{key}", content.encode("utf-8"))
    if failed:
        row.status = ConversionStatus.PARTIAL.value
    else:
        row.status = ConversionStatus.COMPLETED.value
        row.error_code = None
        row.error_message = None
        row.progress = 100
    row.current_page = row.total_pages
    db.commit()
    return _row_to_domain(row)


def requeue_conversion(db: Session, conversion_id: str) -> Conversion:
    """Move FAILED/PARTIAL back to QUEUED so the next run resumes from checkpoints."""
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    if row.status not in (ConversionStatus.FAILED.value, ConversionStatus.PARTIAL.value):
        raise ConflictError(f"Only failed/partial conversions can be re-queued (is {row.status})")
    row.status = ConversionStatus.QUEUED.value
    row.error_code = None
    row.error_message = None
    db.commit()
    return _row_to_domain(row)


def requeue_orphans(db: Session, stale_after_seconds: int = LEASE_SECONDS) -> int:
    """Move PROCESSING conversions with a stale (or missing) heartbeat to QUEUED."""
    cutoff = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
    count = (
        db.query(ConversionRow)
        .filter_by(status=ConversionStatus.PROCESSING.value)
        .filter((ConversionRow.heartbeat_at.is_(None)) | (ConversionRow.heartbeat_at < cutoff))
        .update({"status": ConversionStatus.QUEUED.value}, synchronize_session=False)
    )
    db.commit()
    return count


def queue_conversion(conversion_id: str, settings: Settings | None = None) -> bool:
    """Push the job to Redis; return False (stay queued) when unavailable."""
    try:
        Queue(QUEUE_NAME, connection=get_redis(settings)).enqueue(_JOB_PATH, conversion_id)
        return True
    except Exception:
        logger.warning("queue unavailable; conversion %s stays queued", conversion_id)
        return False


def process_conversion_job(conversion_id: str) -> str:
    """RQ entry — builds deps from settings, runs, returns final status."""
    from app.core.config import get_settings
    from app.infrastructure.database.session import get_session_factory

    settings = get_settings()
    db = get_session_factory()()
    try:
        result = process_conversion(conversion_id, db, LocalStorage(settings.storage_dir), settings)
        return result.status.value
    finally:
        db.close()

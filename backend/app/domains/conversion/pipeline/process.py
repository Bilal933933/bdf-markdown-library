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
from app.domains.conversion.ocr.gemini import GeminiProvider
from app.domains.conversion.ocr.provider import OCRBlockedError, OCRError
from app.domains.conversion.ocr.select import ocr_page_text
from app.domains.conversion.pipeline.hierarchy import normalize_heading_levels
from app.domains.conversion.pipeline.segment import segment_document
from app.domains.conversion.pipeline.structure import detect_blocks
from app.domains.conversion.quality import (
    QualityDecision,
    WordKnown,
    analyze_page,
    get_word_checker,
)
from app.domains.conversion.rendering import build_unit_outputs, collect_stats, render_document
from app.domains.conversion.services.conversions import (
    conversion_from_row,
    list_artifacts,
    load_source_bytes,
    record_event,
    register_artifact,
)
from app.infrastructure.database.tables import ConversionRow, PageCheckpointRow
from app.infrastructure.redis import get_redis
from app.infrastructure.storage import LocalStorage, Storage

logger = logging.getLogger(__name__)

QUEUE_NAME = "conversions"
_JOB_PATH = "app.domains.conversion.pipeline.process.process_conversion_job"
MAX_ATTEMPTS = 3
LEASE_SECONDS = 300
BEAT_EVERY_SECONDS = 60


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


def _accepted(page: Page, method: ExtractionMethod, lexicon: WordKnown | None = None) -> bool:
    result = analyze_page(page, lexicon=lexicon)
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
    retry_rejected: bool = False,
) -> tuple[Page, bool, str | None]:
    """Text first, then OCR; returns (page, accepted, skip note). Never raises.

    retry_rejected skips the text attempt and leads with Gemini (higher DPI,
    retry prompt) for pages whose checkpoint note is quality_rejected.
    """
    image: bytes | None = None
    note: str | None = None
    lexicon = get_word_checker(settings.camel_db_path)
    retry_provider: GeminiProvider | None = None
    if retry_rejected:
        candidate = GeminiProvider.from_settings(settings)
        if candidate.is_available():
            if settings.gemini_retry_prompt.strip():
                candidate.prompt = settings.gemini_retry_prompt
            retry_provider = candidate
    first = 1 if retry_rejected else 0
    for attempt in range(first, MAX_ATTEMPTS):
        try:
            if attempt == 0:
                blocks = detect_blocks(pdf[page_number - 1], pdf_bytes, source_file=source_file)
                page = Page(number=page_number, blocks=blocks)
                if _accepted(page, ExtractionMethod.PYMUPDF, lexicon):
                    return page, True, None
            else:
                if image is None:
                    zoom = 3 if retry_rejected else 2
                    pixmap = pdf[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                    image = pixmap.tobytes("jpg")
                ocr = None
                if retry_provider is not None:
                    try:
                        ocr = retry_provider.ocr(image, "image/jpeg")
                    except OCRError:
                        ocr = None
                if ocr is None:
                    ocr = ocr_page_text(image, "image/jpeg", page_number, settings)
                page = _ocr_blocks_page(ocr.text, page_number, source_file, ocr.method)
                if _accepted(page, ocr.method, lexicon):
                    return page, True, None
        except OCRBlockedError as exc:
            note = f"ocr_refused:{exc}"
            logger.warning("page %d refused by OCR provider", page_number)
        except Exception as exc:
            note = f"{type(exc).__name__}:{exc}"[:200]
            logger.exception("page %d attempt %d failed", page_number, attempt + 1)
    return Page(number=page_number), False, note or "quality_rejected"


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
    if row.status in (ConversionStatus.PAUSED.value, ConversionStatus.CANCELLED.value):
        return _row_to_domain(row)
    if row.status in (ConversionStatus.FAILED.value, ConversionStatus.PARTIAL.value):
        raise ConflictError(f"Conversion {conversion_id} is {row.status}; re-queue it first")
    row.status = ConversionStatus.PROCESSING.value
    _beat(row)
    record_event(db, conversion_id, "started")
    db.commit()

    ext = f".{row.source_file.lower().rsplit('.', 1)[-1]}" if "." in row.source_file else ""
    data, ext = load_source_bytes(db, storage, conversion_id)
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
            db.refresh(row)
            if row.status in (ConversionStatus.PAUSED.value, ConversionStatus.CANCELLED.value):
                db.commit()
                return _row_to_domain(row)
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
            try:
                if pdf_doc is not None:
                    page, accepted, note = _process_page(
                        pdf_doc,
                        page_number,
                        row.source_file,
                        data,
                        resolved,
                        retry_rejected=checkpoint is not None
                        and checkpoint.note == "quality_rejected",
                    )
                else:
                    page = Page(number=page_number, blocks=static_blocks or [])
                    accepted = _accepted(
                        page, static_method, get_word_checker(resolved.camel_db_path)
                    )
                    note = None if accepted else "quality_rejected"
                storage.save(
                    f"{conversion_id}/pages/{page_number}.json", page.model_dump_json().encode()
                )
            except Exception as exc:
                logger.exception("page %d finalize failed, skipping", page_number)
                page, accepted, note = (
                    Page(number=page_number),
                    False,
                    f"finalize_failed:{type(exc).__name__}",
                )
            try:
                if (
                    accepted
                    and page.extraction_method == ExtractionMethod.PYMUPDF
                    and pdf_doc is not None
                ):
                    all_assets.extend(
                        _extract_assets(pdf_doc, page_number, page, conversion_id, storage)
                    )
            except Exception:
                logger.exception("page %d assets skipped", page_number)
            checkpoint.attempts = MAX_ATTEMPTS
            if accepted:
                checkpoint.status = "done"
                checkpoint.method = (page.extraction_method or ExtractionMethod.PYMUPDF).value
                checkpoint.quality = page.quality
                checkpoint.note = None
                qualities.append(page.quality or 0.0)
                done += 1
                record_event(
                    db,
                    conversion_id,
                    "page_done",
                    page_number=page_number,
                    method=checkpoint.method,
                    quality=page.quality,
                )
            else:
                checkpoint.status = "failed"
                checkpoint.note = (note or "failed")[:512]
                failed.append(page_number)
                record_event(db, conversion_id, "page_failed", page_number=page_number, note=note)
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
        record_event(db, conversion_id, "failed", note=row.error_message)
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
    try:
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
        outputs: dict[str, tuple[bytes, str | None, str]] = {
            f"{conversion_id}/output/document.md": (
                render_document(doc, assets_by_id).encode("utf-8"),
                "text/markdown; charset=utf-8",
                "document",
            ),
            f"{conversion_id}/output/metadata.json": (
                doc.metadata.model_dump_json(indent=2).encode(),
                "application/json",
                "metadata",
            ),
            f"{conversion_id}/output/assets.json": (
                json.dumps(
                    [asset.model_dump(mode="json") for asset in doc.assets],
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
                "application/json",
                "assets",
            ),
        }
        for key, content in build_unit_outputs(doc, assets_by_id).items():
            outputs[f"{conversion_id}/output/{key}"] = (content.encode("utf-8"), None, "unit")
        for key, (payload, mime, kind) in outputs.items():
            storage.save(key, payload)
            register_artifact(db, conversion_id, kind, key, payload, mime)
        manifest = {
            "conversion_id": conversion_id,
            "source_file": row.source_file,
            "source_key": row.source_key,
            "source_sha256": row.source_sha256,
            "source_size": row.source_size,
            "artifacts": [a.model_dump(mode="json") for a in list_artifacts(db, conversion_id)],
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        manifest_key = f"{conversion_id}/output/manifest.json"
        storage.save(manifest_key, manifest_bytes)
        register_artifact(db, conversion_id, "manifest", manifest_key, manifest_bytes)
    except Exception as exc:
        logger.exception("conversion %s assembly failed", conversion_id)
        row.status = ConversionStatus.FAILED.value
        row.error_code = ErrorCode.APP_ERROR
        row.error_message = f"assembly failed: {type(exc).__name__}"
        record_event(db, conversion_id, "failed", note=row.error_message)
        db.commit()
        return _row_to_domain(row)
    if failed:
        row.status = ConversionStatus.PARTIAL.value
        record_event(db, conversion_id, "partial", note=f"pages failed quality: {failed}")
    else:
        row.status = ConversionStatus.COMPLETED.value
        row.error_code = None
        row.error_message = None
        row.progress = 100
        record_event(db, conversion_id, "completed")
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
    record_event(db, conversion_id, "requeued")
    db.commit()
    return _row_to_domain(row)


def pause_conversion(db: Session, conversion_id: str) -> Conversion:
    """Move QUEUED/PROCESSING to PAUSED; the worker stops at the next page boundary."""
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    if row.status not in (ConversionStatus.QUEUED.value, ConversionStatus.PROCESSING.value):
        raise ConflictError(f"Only queued/processing conversions can be paused (is {row.status})")
    row.status = ConversionStatus.PAUSED.value
    record_event(db, conversion_id, "paused")
    db.commit()
    return _row_to_domain(row)


def resume_conversion(db: Session, conversion_id: str) -> Conversion:
    """Move PAUSED back to QUEUED so the next run continues from checkpoints."""
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    if row.status != ConversionStatus.PAUSED.value:
        raise ConflictError(f"Only paused conversions can be resumed (is {row.status})")
    row.status = ConversionStatus.QUEUED.value
    record_event(db, conversion_id, "resumed")
    db.commit()
    return _row_to_domain(row)


def cancel_conversion(db: Session, conversion_id: str) -> Conversion:
    """Move QUEUED/PROCESSING/PAUSED to CANCELLED (terminal); drop any queued RQ job."""
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    if row.status not in (
        ConversionStatus.QUEUED.value,
        ConversionStatus.PROCESSING.value,
        ConversionStatus.PAUSED.value,
    ):
        raise ConflictError(
            f"Only queued/processing/paused conversions can be cancelled (is {row.status})"
        )
    row.status = ConversionStatus.CANCELLED.value
    record_event(db, conversion_id, "cancelled")
    db.commit()
    _drop_queued_job(conversion_id)
    return _row_to_domain(row)


def _drop_queued_job(conversion_id: str) -> None:
    """Remove a still-queued RQ job for this conversion; the worker start-guard covers races."""
    try:
        queue = Queue(QUEUE_NAME, connection=get_redis())
        for job_id in list(queue.job_ids):
            job = queue.fetch_job(job_id)
            if job is not None and job.args and str(job.args[0]) == conversion_id:
                job.cancel()
    except Exception:
        logger.warning("could not drop queued job for conversion %s", conversion_id)


def requeue_orphans(db: Session, stale_after_seconds: int = LEASE_SECONDS) -> int:
    """Move PROCESSING conversions with a stale (or missing) heartbeat to QUEUED."""
    cutoff = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
    count = (
        db.query(ConversionRow)
        .filter_by(status=ConversionStatus.PROCESSING.value)
        .filter((ConversionRow.heartbeat_at.is_(None)) | (ConversionRow.heartbeat_at <= cutoff))
        .update({"status": ConversionStatus.QUEUED.value}, synchronize_session=False)
    )
    db.commit()
    return count


def enqueue_missing_jobs(db: Session, stale_after_seconds: int = LEASE_SECONDS) -> int:
    """Enqueue stale QUEUED conversions with no active job (lost on worker death)."""
    try:
        connection = get_redis()
    except Exception:
        return 0
    queue = Queue(QUEUE_NAME, connection=connection)
    active: set[str] = set()
    try:
        from rq.registry import StartedJobRegistry

        job_ids = (
            list(queue.job_ids)
            + StartedJobRegistry(QUEUE_NAME, connection=connection).get_job_ids()
        )
        for job_id in job_ids:
            job = queue.fetch_job(job_id)
            if job is not None and job.args:
                active.add(str(job.args[0]))
    except Exception:
        logger.warning("could not inspect queue registries")
        return 0
    cutoff = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
    rows = (
        db.query(ConversionRow)
        .filter_by(status=ConversionStatus.QUEUED.value)
        .filter(ConversionRow.created_at <= cutoff)
        .all()
    )
    enqueued = 0
    for row in rows:
        if row.id not in active and queue_conversion(row.id):
            enqueued += 1
    return enqueued


def queue_conversion(conversion_id: str, settings: Settings | None = None) -> bool:
    """Push the job to Redis; return False (stay queued) when unavailable."""
    try:
        Queue(QUEUE_NAME, connection=get_redis(settings)).enqueue(_JOB_PATH, conversion_id)
        return True
    except Exception:
        logger.warning("queue unavailable; conversion %s stays queued", conversion_id)
        return False


def process_conversion_job(conversion_id: str) -> str:
    """RQ entry — builds deps from settings, beats while running, returns status."""
    import threading

    from app.core.config import get_settings
    from app.infrastructure.database.session import get_session_factory

    settings = get_settings()
    db = get_session_factory()()
    beat_db = get_session_factory()()
    stop = threading.Event()

    def beat_forever() -> None:
        while not stop.wait(BEAT_EVERY_SECONDS):
            try:
                row = beat_db.get(ConversionRow, conversion_id)
                if row is None:
                    return
                _beat(row)
                beat_db.commit()
            except Exception:
                beat_db.rollback()

    thread = threading.Thread(target=beat_forever, daemon=True)
    thread.start()
    try:
        result = process_conversion(conversion_id, db, LocalStorage(settings.storage_dir), settings)
        return result.status.value
    finally:
        stop.set()
        thread.join(timeout=5)
        beat_db.close()
        db.close()

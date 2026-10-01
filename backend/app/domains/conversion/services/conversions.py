"""Conversion intake and status reads — file validation, page count, persistence.

No HTTP here. No queueing here either (worker slice): new conversions stay queued.
"""

import hashlib
import uuid

import pymupdf
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors.exceptions import NotFoundError, ValidationError
from app.domains.conversion.extract import decode_text
from app.domains.conversion.models import (
    Conversion,
    ConversionError,
    ConversionStatus,
    OutputArtifact,
)
from app.domains.conversion.schemas import ConversionEvent
from app.infrastructure.database.tables import (
    ArtifactRow,
    ConversionEventRow,
    ConversionRow,
    PageCheckpointRow,
)
from app.infrastructure.storage import Storage

_PDF_MAGIC = b"%PDF-"
_DOCX_MAGIC = b"PK\x03\x04"
_PNG_MAGIC = b"\x89PNG"
_JPG_MAGIC = b"\xff\xd8\xff"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
_WEBP_EXT = ".webp"
_ACCEPTED = "Only PDF, DOCX, TXT, PNG, JPG, and WebP files are accepted in V1"
_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _current_request_id() -> str | None:
    try:
        from app.core.logging import get_request_id

        return get_request_id()
    except Exception:
        return None


def _is_webp(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _count_pdf_pages(data: bytes) -> int:
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            return len(doc)
    except Exception as exc:
        raise ValidationError("Invalid PDF file", details={"reason": "unreadable"}) from exc


def _extension(filename: str) -> str:
    return f".{filename.lower().rsplit('.', 1)[-1]}" if "." in filename else ""


def create_conversion(
    db: Session,
    storage: Storage,
    filename: str,
    data: bytes,
    settings: Settings,
) -> Conversion:
    """Validate, store input, insert conversion + per-page checkpoints. Returns queued."""
    if len(data) > settings.max_file_size:
        raise ValidationError(
            "File exceeds size limit",
            details={"max_file_size": settings.max_file_size, "actual": len(data)},
        )
    if not data:
        raise ValidationError("File is empty", details={"filename": filename})
    ext = _extension(filename)
    if ext == ".pdf":
        if not data.startswith(_PDF_MAGIC):
            raise ValidationError("Invalid PDF file", details={"filename": filename})
        total_pages = _count_pdf_pages(data)
        if total_pages < 1:
            raise ValidationError("PDF has no pages", details={"filename": filename})
        if total_pages > settings.max_pages:
            raise ValidationError(
                "PDF exceeds page limit",
                details={"max_pages": settings.max_pages, "actual": total_pages},
            )
    elif ext == ".docx":
        if not data.startswith(_DOCX_MAGIC):
            raise ValidationError("Invalid DOCX file", details={"filename": filename})
        total_pages = 1
    elif ext == ".txt":
        decode_text(data)
        total_pages = 1
    elif ext in _IMAGE_EXTS:
        if not (data.startswith(_PNG_MAGIC) or data.startswith(_JPG_MAGIC)):
            raise ValidationError("Invalid image file", details={"filename": filename})
        total_pages = 1
    elif ext == _WEBP_EXT:
        if not _is_webp(data):
            raise ValidationError("Invalid image file", details={"filename": filename})
        total_pages = 1
    else:
        raise ValidationError(_ACCEPTED, details={"filename": filename})

    conversion_id = uuid.uuid4().hex
    source_key = f"{conversion_id}/original{ext}"
    storage.save(source_key, data)
    db.add(
        ConversionRow(
            id=conversion_id,
            source_file=filename,
            source_key=source_key,
            source_sha256=_sha256(data),
            source_size=len(data),
            source_mime=_MIME_BY_EXT.get(ext),
            status=ConversionStatus.QUEUED.value,
            total_pages=total_pages,
        )
    )
    for page_number in range(1, total_pages + 1):
        db.add(PageCheckpointRow(conversion_id=conversion_id, page_number=page_number))
    record_event(db, conversion_id, "queued", note=f"{total_pages} pages")
    db.commit()
    return Conversion(
        id=conversion_id,
        source_file=filename,
        status=ConversionStatus.QUEUED,
        total_pages=total_pages,
        source_key=source_key,
        source_sha256=_sha256(data),
        source_size=len(data),
        source_mime=_MIME_BY_EXT.get(ext),
    )


def conversion_from_row(row: ConversionRow) -> Conversion:
    """Map a persistence row to the domain model."""
    error = (
        ConversionError(code=row.error_code, message=row.error_message or "")
        if row.error_code
        else None
    )
    return Conversion(
        id=row.id,
        source_file=row.source_file,
        status=ConversionStatus(row.status),
        progress=row.progress,
        total_pages=row.total_pages,
        current_page=row.current_page,
        error=error,
        source_key=row.source_key,
        source_sha256=row.source_sha256,
        source_size=row.source_size,
        source_mime=row.source_mime,
    )


def get_conversion(db: Session, conversion_id: str) -> Conversion:
    """Return the Conversion or raise 404."""
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    return conversion_from_row(row)


def list_conversions(db: Session, limit: int = 20, offset: int = 0) -> list[Conversion]:
    """Newest first, paginated."""
    rows = (
        db.query(ConversionRow)
        .order_by(ConversionRow.created_at.desc(), ConversionRow.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [conversion_from_row(row) for row in rows]


def record_event(
    db: Session,
    conversion_id: str,
    kind: str,
    page_number: int | None = None,
    method: str | None = None,
    quality: float | None = None,
    note: str | None = None,
    request_id: str | None = None,
) -> None:
    """Append one event row; flushed with the caller's transaction (no commit here)."""
    db.add(
        ConversionEventRow(
            conversion_id=conversion_id,
            kind=kind,
            request_id=request_id if request_id is not None else _current_request_id(),
            page_number=page_number,
            method=method,
            quality=quality,
            note=(note[:512] if note else None),
        )
    )
    db.flush()


def load_source_bytes(db: Session, storage: Storage, conversion_id: str) -> tuple[bytes, str]:
    """Return (bytes, ext) for the stored original; falls back to legacy input<ext>."""
    row = db.get(ConversionRow, conversion_id)
    if row is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    ext = f".{row.source_file.lower().rsplit('.', 1)[-1]}" if "." in row.source_file else ""
    candidates = [
        row.source_key or "",
        f"{conversion_id}/original{ext}",
        f"{conversion_id}/input{ext}",
    ]
    last_error: Exception | None = None
    for key in candidates:
        if not key:
            continue
        try:
            return storage.load(key), ext
        except (FileNotFoundError, ValueError) as exc:
            last_error = exc
    raise NotFoundError(f"Source for {conversion_id} not found") from last_error


def artifact_from_row(row: ArtifactRow) -> OutputArtifact:
    """Map a persistence row to the domain model."""
    return OutputArtifact(
        id=row.id,
        conversion_id=row.conversion_id,
        kind=row.kind,
        key=row.key,
        sha256=row.sha256,
        size=row.size,
        mime=row.mime,
    )


def register_artifact(
    db: Session,
    conversion_id: str,
    kind: str,
    key: str,
    payload: bytes,
    mime: str | None = None,
) -> OutputArtifact:
    """Track one output file by id + content hash; flushed with the caller's transaction."""
    artifact = OutputArtifact(
        id=uuid.uuid4().hex,
        conversion_id=conversion_id,
        kind=kind,
        key=key,
        sha256=_sha256(payload),
        size=len(payload),
        mime=mime,
    )
    db.add(
        ArtifactRow(
            id=artifact.id,
            conversion_id=conversion_id,
            kind=kind,
            key=key,
            sha256=artifact.sha256,
            size=artifact.size,
            mime=mime,
        )
    )
    db.flush()
    return artifact


def list_artifacts(db: Session, conversion_id: str) -> list[OutputArtifact]:
    """Tracked outputs oldest first, or raise 404 for unknown conversions."""
    if db.get(ConversionRow, conversion_id) is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    rows = (
        db.query(ArtifactRow)
        .filter_by(conversion_id=conversion_id)
        .order_by(ArtifactRow.created_at.asc(), ArtifactRow.id.asc())
        .all()
    )
    return [artifact_from_row(row) for row in rows]


def list_events(db: Session, conversion_id: str) -> list[ConversionEvent]:
    """Event log oldest first, or raise 404 for unknown conversions.

    Recorded events come first; pages finished before logging existed are
    backfilled from checkpoints (done/failed only — pending says nothing).
    """
    if db.get(ConversionRow, conversion_id) is None:
        raise NotFoundError(f"Conversion {conversion_id} not found")
    rows = (
        db.query(ConversionEventRow)
        .filter_by(conversion_id=conversion_id)
        .order_by(ConversionEventRow.id.asc())
        .all()
    )
    events = [
        ConversionEvent(
            id=row.id,
            kind=row.kind,
            request_id=row.request_id,
            page_number=row.page_number,
            method=row.method,
            quality=row.quality,
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]
    logged_pages = {
        e.page_number
        for e in events
        if e.page_number is not None and e.kind in ("page_done", "page_failed")
    }
    checkpoints = (
        db.query(PageCheckpointRow)
        .filter_by(conversion_id=conversion_id)
        .filter(PageCheckpointRow.status.in_(("done", "failed")))
        .order_by(PageCheckpointRow.page_number.asc())
        .all()
    )
    for cp in checkpoints:
        if cp.page_number in logged_pages:
            continue
        events.append(
            ConversionEvent(
                id=0,
                kind=f"page_{cp.status}",
                page_number=cp.page_number,
                method=cp.method,
                quality=cp.quality,
                note=cp.note,
            )
        )
    return events

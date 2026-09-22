"""Conversion intake and status reads — file validation, page count, persistence.

No HTTP here. No queueing here either (worker slice): new conversions stay queued.
"""

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
)
from app.infrastructure.database.tables import ConversionRow, PageCheckpointRow
from app.infrastructure.storage import Storage

_PDF_MAGIC = b"%PDF-"
_DOCX_MAGIC = b"PK\x03\x04"
_PNG_MAGIC = b"\x89PNG"
_JPG_MAGIC = b"\xff\xd8\xff"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
_WEBP_EXT = ".webp"
_ACCEPTED = "Only PDF, DOCX, TXT, PNG, JPG, and WebP files are accepted in V1"


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
    storage.save(f"{conversion_id}/input{ext}", data)
    db.add(
        ConversionRow(
            id=conversion_id,
            source_file=filename,
            status=ConversionStatus.QUEUED.value,
            total_pages=total_pages,
        )
    )
    for page_number in range(1, total_pages + 1):
        db.add(PageCheckpointRow(conversion_id=conversion_id, page_number=page_number))
    db.commit()
    return Conversion(
        id=conversion_id,
        source_file=filename,
        status=ConversionStatus.QUEUED,
        total_pages=total_pages,
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

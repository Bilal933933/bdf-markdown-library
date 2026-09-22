"""Closed vocabularies of the Document Model."""

from enum import StrEnum


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    QUOTE = "quote"
    CODE = "code"


class ExtractionMethod(StrEnum):
    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"
    PADDLEOCR = "paddleocr"
    GEMINI = "gemini"
    TESSERACT = "tesseract"
    DOCX = "docx"
    TEXT = "text"


class UnitStatus(StrEnum):
    CONFIRMED = "confirmed"
    UNKNOWN_SECTION = "unknown_section"


class ConversionStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CheckpointStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"

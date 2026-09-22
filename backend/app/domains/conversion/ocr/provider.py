"""OCR contracts — provider protocol and result (no network, no weights)."""

from typing import Protocol

from pydantic import BaseModel, Field

from app.domains.conversion.models import ExtractionMethod


class OCRResult(BaseModel):
    text: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: ExtractionMethod


class OCRError(Exception):
    """Any OCR failure that selection may fall through or surface."""


class OCRUnavailableError(OCRError):
    """No usable provider (missing lib, no keys)."""


class OCRBlockedError(OCRError):
    """Provider refused (recitation/safety) — not retried, not stored as text."""


class OCRProvider(Protocol):
    name: ExtractionMethod

    def is_available(self) -> bool: ...

    def ocr(self, image: bytes, mime: str) -> OCRResult: ...

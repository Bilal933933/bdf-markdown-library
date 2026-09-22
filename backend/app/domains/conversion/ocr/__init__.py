"""OCR public API — providers plus page-level selection."""

from app.domains.conversion.ocr.gemini import GeminiProvider
from app.domains.conversion.ocr.paddle import PaddleProvider
from app.domains.conversion.ocr.provider import (
    OCRBlockedError,
    OCRError,
    OCRProvider,
    OCRResult,
    OCRUnavailableError,
)
from app.domains.conversion.ocr.select import ocr_page_text

__all__ = [
    "GeminiProvider",
    "OCRBlockedError",
    "OCRError",
    "OCRProvider",
    "OCRResult",
    "OCRUnavailableError",
    "PaddleProvider",
    "ocr_page_text",
]

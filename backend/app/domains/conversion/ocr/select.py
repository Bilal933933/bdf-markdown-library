"""Provider selection — Paddle first, Gemini fallback, judged by analyze_page."""

from app.core.config import Settings
from app.domains.conversion.models import (
    Block,
    BlockSource,
    BlockType,
    ExtractionMethod,
    Page,
    ParagraphPayload,
)
from app.domains.conversion.ocr.gemini import GeminiProvider
from app.domains.conversion.ocr.paddle import PaddleProvider
from app.domains.conversion.ocr.provider import (
    OCRError,
    OCRProvider,
    OCRResult,
    OCRUnavailableError,
)
from app.domains.conversion.quality import QualityDecision, analyze_page


def _as_page(text: str, page_number: int, method: ExtractionMethod) -> Page:
    return Page(
        number=page_number,
        blocks=[
            Block(
                id=f"p{page_number}-b0",
                type=BlockType.PARAGRAPH,
                order=0,
                source=BlockSource(file="ocr", pages=[page_number], method=method),
                payload=ParagraphPayload(text=text),
            )
        ],
    )


def ocr_page_text(
    image: bytes,
    mime: str,
    page_number: int,
    settings: Settings,
    paddle: OCRProvider | None = None,
    gemini: OCRProvider | None = None,
) -> OCRResult:
    """OCR one page image; Paddle when accepted, else Gemini. Raises when stuck."""
    primary = paddle or PaddleProvider()
    fallback = gemini or GeminiProvider.from_settings(settings)
    if primary.is_available():
        try:
            result = primary.ocr(image, mime)
        except OCRError:
            result = None
        if result is not None:
            judged = analyze_page(_as_page(result.text, page_number, result.method))
            if judged.decision == QualityDecision.ACCEPT:
                return result
    if not fallback.is_available():
        raise OCRUnavailableError("no OCR provider available")
    return fallback.ocr(image, mime)

"""PaddleOCR provider — primary engine, lazy import (weights not bundled).

Live verification against real weights is a later stage; until then this adapter
is exercised through mocks, and parsing tolerates known result shapes.
"""

from typing import Any

from app.domains.conversion.models import ExtractionMethod
from app.domains.conversion.ocr.provider import OCRResult, OCRUnavailableError


class PaddleProvider:
    name = ExtractionMethod.PADDLEOCR

    def __init__(self, lang: str = "ar") -> None:
        self.lang = lang

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
        except ImportError:
            return False
        return True

    def ocr(self, image: bytes, mime: str) -> OCRResult:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OCRUnavailableError("paddleocr is not installed") from exc
        pixels = _decode(image)
        engine: Any = PaddleOCR(lang=self.lang)
        predict = getattr(engine, "predict", None)
        raw = predict(pixels) if callable(predict) else engine.ocr(pixels)
        texts, scores = _parse(raw)
        confidence = sum(scores) / len(scores) if scores else None
        return OCRResult(text="\n".join(texts), confidence=confidence, method=self.name)


def _decode(image: bytes) -> Any:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise OCRUnavailableError("numpy/cv2 needed to feed PaddleOCR") from exc
    pixels = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
    if pixels is None:
        raise OCRUnavailableError("could not decode OCR image")
    return pixels


def _parse(raw: Any) -> tuple[list[str], list[float]]:
    texts: list[str] = []
    scores: list[float] = []
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        if isinstance(item, dict):
            texts.extend(str(t) for t in item.get("rec_texts", []))
            scores.extend(float(s) for s in item.get("rec_scores", []))
        elif isinstance(item, (list, tuple)):
            for entry in item:
                if (
                    isinstance(entry, (list, tuple))
                    and len(entry) == 2
                    and isinstance(entry[1], (list, tuple))
                ):
                    texts.append(str(entry[1][0]))
                    scores.append(float(entry[1][1]))
    return texts, scores

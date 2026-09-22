import httpx
import pytest

from app.core.config import Settings
from app.domains.conversion.models import ExtractionMethod
from app.domains.conversion.ocr import (
    GeminiProvider,
    OCRBlockedError,
    OCRError,
    OCRResult,
    OCRUnavailableError,
    PaddleProvider,
    ocr_page_text,
)

GOOD_ARABIC = "المبتدأ اسم مرفوع يقع في أول الجملة والخبر يتمم معناه ويكمل الفائدة للمستمع والقارئ"
FAKE_IMAGE = b"\xff\xd8fake-jpeg"


class FakeProvider:
    def __init__(self, method: ExtractionMethod, text: str = "", available: bool = True) -> None:
        self.name = method
        self.text = text
        self.available = available
        self.calls = 0

    def is_available(self) -> bool:
        return self.available

    def ocr(self, image: bytes, mime: str) -> OCRResult:
        self.calls += 1
        return OCRResult(text=self.text, confidence=None, method=self.name)


def empty_settings() -> Settings:
    return Settings(gemini_keys="", gemini_api_key="")


def gemini_ok(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}


def test_paddle_accepted_skips_gemini() -> None:
    paddle = FakeProvider(ExtractionMethod.PADDLEOCR, GOOD_ARABIC)
    gemini = FakeProvider(ExtractionMethod.GEMINI, GOOD_ARABIC)
    result = ocr_page_text(
        FAKE_IMAGE, "image/jpeg", 1, empty_settings(), paddle=paddle, gemini=gemini
    )
    assert result.method == ExtractionMethod.PADDLEOCR
    assert gemini.calls == 0


def test_weak_paddle_falls_back_to_gemini() -> None:
    paddle = FakeProvider(ExtractionMethod.PADDLEOCR, "؟؟؟")
    gemini = FakeProvider(ExtractionMethod.GEMINI, GOOD_ARABIC)
    result = ocr_page_text(
        FAKE_IMAGE, "image/jpeg", 1, empty_settings(), paddle=paddle, gemini=gemini
    )
    assert result.method == ExtractionMethod.GEMINI
    assert gemini.calls == 1


def test_no_provider_available_raises() -> None:
    with pytest.raises(OCRUnavailableError):
        ocr_page_text(
            FAKE_IMAGE,
            "image/jpeg",
            1,
            empty_settings(),
            paddle=FakeProvider(ExtractionMethod.PADDLEOCR, available=False),
            gemini=FakeProvider(ExtractionMethod.GEMINI, available=False),
        )


def test_gemini_parses_candidate_text() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=gemini_ok("نص")))
    provider = GeminiProvider(keys=["k"], models=["m"], prompt="p", transport=transport)
    assert provider.ocr(FAKE_IMAGE, "image/jpeg").text == "نص"


def test_gemini_quota_rotates_to_next_model() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "m1:" in str(request.url):
            return httpx.Response(429, json={"error": {"message": "quota"}})
        return httpx.Response(200, json=gemini_ok("نص"))

    provider = GeminiProvider(
        keys=["k"], models=["m1", "m2"], prompt="p", transport=httpx.MockTransport(handler)
    )
    assert provider.ocr(FAKE_IMAGE, "image/jpeg").text == "نص"
    assert len(seen) == 2


def test_gemini_recitation_raises_blocked() -> None:
    payload = {"candidates": [{"content": {"parts": []}, "finishReason": "RECITATION"}]}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    provider = GeminiProvider(keys=["k"], models=["m"], prompt="p", transport=transport)
    with pytest.raises(OCRBlockedError):
        provider.ocr(FAKE_IMAGE, "image/jpeg")


def test_gemini_empty_response_raises() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    provider = GeminiProvider(keys=["k"], models=["m"], prompt="p", transport=transport)
    with pytest.raises(OCRError):
        provider.ocr(FAKE_IMAGE, "image/jpeg")


def test_gemini_retries_timeout_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("slow")
        return httpx.Response(200, json=gemini_ok("نص"))

    provider = GeminiProvider(
        keys=["k"], models=["m"], prompt="p", transport=httpx.MockTransport(handler)
    )
    assert provider.ocr(FAKE_IMAGE, "image/jpeg").text == "نص"
    assert calls["n"] == 2


def test_paddle_unavailable_without_library() -> None:
    assert PaddleProvider().is_available() is False


def test_gemini_unavailable_without_keys() -> None:
    assert GeminiProvider.from_settings(empty_settings()).is_available() is False

"""Gemini fallback OCR — direct REST, same contract as the _ocr scripts.

Keys rotate outer, models inner; quota (429/503) moves on, network blips retry
via Tenacity, RECITATION/SAFETY raises (never stored as page text).
"""

import base64
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.domains.conversion.models import ExtractionMethod
from app.domains.conversion.ocr.provider import (
    OCRBlockedError,
    OCRError,
    OCRResult,
    OCRUnavailableError,
)

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_TIMEOUT = 120.0
_BLOCKED_REASONS = {"RECITATION", "SAFETY"}


class _QuotaExhausted(Exception):
    pass


class GeminiProvider:
    name = ExtractionMethod.GEMINI

    def __init__(
        self,
        keys: list[str],
        models: list[str],
        prompt: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.keys = keys
        self.models = models
        self.prompt = prompt
        self.transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: httpx.BaseTransport | None = None
    ) -> "GeminiProvider":
        keys = [k.strip() for k in settings.gemini_keys.split(",") if k.strip()]
        if settings.gemini_api_key.strip():
            keys.append(settings.gemini_api_key.strip())
        models = [settings.gemini_model.strip()]
        models.extend(m.strip() for m in settings.gemini_fallback.split(",") if m.strip())
        seen = list(dict.fromkeys(m for m in models if m))
        return cls(keys=keys, models=seen, prompt=settings.gemini_prompt, transport=transport)

    def is_available(self) -> bool:
        return bool(self.keys and self.models)

    def ocr(self, image: bytes, mime: str) -> OCRResult:
        if not self.is_available():
            raise OCRUnavailableError("no Gemini keys/models configured")
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": self.prompt},
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": base64.b64encode(image).decode(),
                            }
                        },
                    ]
                }
            ]
        }
        last: Exception = OCRError("no Gemini model responded")
        for key in self.keys:
            for model in self.models:
                try:
                    with httpx.Client(timeout=_TIMEOUT, transport=self.transport) as client:
                        response = self._post(client, key, model, body)
                    return OCRResult(
                        text=_parse(response.json()), confidence=None, method=self.name
                    )
                except _QuotaExhausted as exc:
                    last = exc
                    continue
        raise last

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    def _post(
        self, client: httpx.Client, key: str, model: str, body: dict[str, Any]
    ) -> httpx.Response:
        response = client.post(_ENDPOINT.format(model=model), params={"key": key}, json=body)
        if response.status_code in (429, 503):
            raise _QuotaExhausted(f"{model} returned {response.status_code}")
        if response.status_code >= 400:
            raise OCRError(f"Gemini returned {response.status_code}")
        return response


def _parse(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        raise OCRError("empty Gemini response")
    first = candidates[0]
    if first.get("finishReason") in _BLOCKED_REASONS:
        raise OCRBlockedError(f"Gemini refused: {first.get('finishReason')}")
    parts = first.get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise OCRError("empty Gemini response")
    return text

"""Page quality analyzer — independent gate after OCR (pure, no IO).

Thresholds are V1 starting points, tunable when real OCR data arrives.
Deferred: invalid-word dictionary, line order, table quality (added on real need).
"""

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.conversion.models import (
    CodePayload,
    ListPayload,
    Page,
    TablePayload,
)

_MIN_USEFUL_CHARS = 20
_ACCEPT_SCORE = 0.75
_RETRY_SCORE = 0.45
_ARABIC_FLOOR = 0.5
_MIN_WORDS_FOR_REPETITION = 10
_UNIQUE_WORD_FLOOR = 0.6

_CONTROL_CODES = (
    list(range(0x00, 0x20))
    + list(range(0x7F, 0xA0))
    + [0x200B, 0x200C, 0x200D, 0x200E, 0x200F]
    + [0x202A, 0x202B, 0x202C, 0x202D, 0x202E]
    + [0xFEFF, 0xFFFD]
)
_CONTROL_SET = {chr(code) for code in _CONTROL_CODES}


def _count_control(text: str) -> int:
    return sum(1 for char in text if char in _CONTROL_SET)


def _is_arabic(char: str) -> bool:
    code = ord(char)
    return (
        0x0600 <= code <= 0x06FF
        or 0x0750 <= code <= 0x077F
        or 0xFB50 <= code <= 0xFDFF
        or 0xFE70 <= code <= 0xFEFF
    )


class QualityDecision(StrEnum):
    ACCEPT = "accept"
    RETRY = "retry"
    GEMINI = "gemini"


class QualityResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    decision: QualityDecision
    reasons: list[str] = Field(default_factory=list)


def _block_texts(page: Page) -> tuple[str, str]:
    full: list[str] = []
    no_code: list[str] = []
    for block in page.blocks:
        payload = block.payload
        if isinstance(payload, CodePayload):
            text = payload.text
            full.append(text)
        elif isinstance(payload, ListPayload):
            text = " ".join(item.text for item in payload.items)
            full.append(text)
            no_code.append(text)
        elif isinstance(payload, TablePayload):
            text = " ".join(cell.text for row in payload.rows for cell in row.cells)
            full.append(text)
            no_code.append(text)
        elif hasattr(payload, "text"):
            full.append(str(payload.text))
            no_code.append(str(payload.text))
        elif hasattr(payload, "caption") and payload.caption:
            full.append(str(payload.caption))
            no_code.append(str(payload.caption))
    return " ".join(full), " ".join(no_code)


def analyze_page(page: Page) -> QualityResult:
    """Score one page and decide accept / retry / gemini fallback."""
    full_text, lang_text = _block_texts(page)
    useful = re.sub(r"\s+", "", full_text)
    if len(useful) < _MIN_USEFUL_CHARS:
        return QualityResult(
            score=0.0, decision=QualityDecision.RETRY, reasons=["empty_or_too_short"]
        )

    penalties: list[tuple[str, float]] = []
    control = _count_control(full_text)
    if control:
        penalties.append(("control_chars", min(0.6, control / (len(useful) + 1) * 2)))

    letters = [c for c in lang_text if c.isalpha()]
    if letters:
        ratio = sum(1 for c in letters if _is_arabic(c)) / len(letters)
        if ratio < _ARABIC_FLOOR:
            penalties.append(("low_arabic_ratio", min(0.4, (_ARABIC_FLOOR - ratio) * 0.8)))

    words = full_text.split()
    if len(words) >= _MIN_WORDS_FOR_REPETITION:
        uniqueness = len(set(words)) / len(words)
        if uniqueness < _UNIQUE_WORD_FLOOR:
            penalties.append(("repeated_text", min(0.5, (1 - uniqueness) * 0.8)))

    score = max(0.0, min(1.0, 1.0 - sum(p for _, p in penalties)))
    if score >= _ACCEPT_SCORE:
        decision = QualityDecision.ACCEPT
    elif score >= _RETRY_SCORE:
        decision = QualityDecision.RETRY
    else:
        decision = QualityDecision.GEMINI
    return QualityResult(
        score=round(score, 3), decision=decision, reasons=[r for r, _ in penalties]
    )

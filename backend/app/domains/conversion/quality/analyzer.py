"""Page quality analyzer — independent gate after OCR (pure, no IO).

Thresholds are V1 starting points, tunable when real OCR data arrives.
Optional injected lexicon (e.g. CAMeL calima-msa wordlist) enables the
camel_oov penalty; diacritic-heavy pages are flagged, never rewritten.
Deferred: line order, table quality (added on real need).
"""

import re
from collections.abc import Callable, Collection
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
_MIN_WORDS_FOR_CAMEL = 10
_CAMEL_OOV_CAP = 0.5
_DIACRITIC_WORD_FLOOR = 0.3
_MIN_WORDS_FOR_FRAGMENT = 10
_FRAGMENT_KNEE = 0.2
_FRAGMENT_CAP = 0.6
_MIN_WORDS_FOR_MIXED = 10
_MIXED_KNEE = 0.1
_MIXED_CAP = 0.6

_DIACRITICS = re.compile(r"[ً-ٰٟ]")

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


def _lexeme(word: str) -> str:
    return "".join(char for char in _DIACRITICS.sub("", word) if char.isalpha())


def _known(lexicon: Collection[str] | Callable[[str], bool], word: str) -> bool:
    if callable(lexicon):
        return bool(lexicon(word))
    return word in lexicon


def _camel_stats(
    text: str, lexicon: Collection[str] | Callable[[str], bool]
) -> tuple[float | None, bool]:
    raw = text.split()
    lexemes = [_lexeme(word) for word in raw]
    lexemes = [word for word in lexemes if word]
    if len(lexemes) < _MIN_WORDS_FOR_CAMEL:
        return None, False
    unknown = sum(1 for word in lexemes if not _known(lexicon, word))
    oov = unknown / len(lexemes) if unknown else None
    vocalized = sum(1 for word in raw if _DIACRITICS.search(word))
    return oov, vocalized / len(raw) >= _DIACRITIC_WORD_FLOOR if raw else False


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


def analyze_page(
    page: Page, *, lexicon: Collection[str] | Callable[[str], bool] | None = None
) -> QualityResult:
    """Score one page and decide accept / retry / gemini fallback."""
    full_text, lang_text = _block_texts(page)
    useful = re.sub(r"\s+", "", full_text)
    if len(useful) < _MIN_USEFUL_CHARS:
        return QualityResult(
            score=0.0, decision=QualityDecision.RETRY, reasons=["empty_or_too_short"]
        )

    penalties: list[tuple[str, float]] = []
    flags: list[str] = []
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

    lexemes = [_lexeme(word) for word in lang_text.split()]
    lexemes = [word for word in lexemes if word]
    if len(lexemes) >= _MIN_WORDS_FOR_FRAGMENT:
        tiny = sum(1 for word in lexemes if len(word) <= 2)
        frag = tiny / len(lexemes)
        if frag > _FRAGMENT_KNEE:
            penalties.append(("fragmented_text", min(_FRAGMENT_CAP, (frag - _FRAGMENT_KNEE) * 1.2)))

    arabic_words = [word for word in lang_text.split() if any(_is_arabic(char) for char in word)]
    if len(arabic_words) >= _MIN_WORDS_FOR_MIXED:
        mixed = sum(
            1
            for word in arabic_words
            if any(char.isascii() and char.isdigit() or "٠" <= char <= "٩" for char in word)
        ) / len(arabic_words)
        if mixed > _MIXED_KNEE:
            penalties.append(("mixed_alnum", min(_MIXED_CAP, (mixed - _MIXED_KNEE) * 2.0)))

    if lexicon is not None:
        oov, vocalized = _camel_stats(lang_text, lexicon)
        if oov is not None:
            penalties.append(("camel_oov", min(_CAMEL_OOV_CAP, oov * 0.8)))
        if vocalized:
            flags.append("diacritic_suspect")

    score = max(0.0, min(1.0, 1.0 - sum(p for _, p in penalties)))
    if score >= _ACCEPT_SCORE:
        decision = QualityDecision.ACCEPT
    elif score >= _RETRY_SCORE:
        decision = QualityDecision.RETRY
    else:
        decision = QualityDecision.GEMINI
    return QualityResult(
        score=round(score, 3),
        decision=decision,
        reasons=[r for r, _ in penalties] + flags,
    )

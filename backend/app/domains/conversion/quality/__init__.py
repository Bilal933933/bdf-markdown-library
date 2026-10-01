"""Quality gate public API — page-level OCR verdicts."""

from app.domains.conversion.quality.analyzer import (
    QualityDecision,
    QualityResult,
    analyze_page,
)
from app.domains.conversion.quality.lexicon import WordKnown, get_word_checker

__all__ = ["QualityDecision", "QualityResult", "WordKnown", "analyze_page", "get_word_checker"]

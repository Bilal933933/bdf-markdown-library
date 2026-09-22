"""Quality gate public API — page-level OCR verdicts."""

from app.domains.conversion.quality.analyzer import (
    QualityDecision,
    QualityResult,
    analyze_page,
)

__all__ = ["QualityDecision", "QualityResult", "analyze_page"]

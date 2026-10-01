"""CAMeL-backed word lookup for the quality gate (lazy, cached, optional).

The 40MB CALIMA database loads once per process on first use (~9s);
callers pass the returned predicate as ``lexicon`` to ``analyze_page``.
Empty or missing path disables the slice without touching V1 behavior.
"""

from collections.abc import Callable
from functools import cache
from pathlib import Path

WordKnown = Callable[[str], bool]


@cache
def get_word_checker(db_path: str | None) -> WordKnown | None:
    """Return a word-membership predicate, or None when disabled/unavailable."""
    if not db_path or not Path(db_path).is_file():
        return None
    from camel_tools.morphology.analyzer import Analyzer
    from camel_tools.morphology.database import MorphologyDB

    # Strict lookup: default backoff invents analyses for unknown words,
    # which would hide OCR garbage from the OOV penalty.
    analyzer = Analyzer(MorphologyDB(str(db_path), "a"), backoff="NONE")
    seen: dict[str, bool] = {}

    def known(word: str) -> bool:
        hit = seen.get(word)
        if hit is None:
            hit = bool(analyzer.analyze(word))
            seen[word] = hit
        return hit

    return known

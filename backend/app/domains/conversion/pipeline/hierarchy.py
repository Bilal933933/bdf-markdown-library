"""Hierarchy detection — global heading-level correction (pure, no IO).

Per-page detection ranks sizes locally, so concatenating pages can produce
level jumps (e.g. 1 followed by 3). This pass clamps them in document order.
Building Unit/Lesson belongs to the later Segmentation layer, not here.
"""

from app.domains.conversion.models import (
    Document,
    HeadingPayload,
)


def normalize_heading_levels(doc: Document) -> Document:
    """Return a copy with heading levels clamped to a valid outline sequence."""
    result = doc.model_copy(deep=True)
    prev = 0
    for page in sorted(result.pages, key=lambda p: p.number):
        for block in sorted(page.blocks, key=lambda b: b.order):
            payload = block.payload
            if not isinstance(payload, HeadingPayload):
                continue
            payload.level = min(payload.level, prev + 1)
            prev = payload.level
    return result

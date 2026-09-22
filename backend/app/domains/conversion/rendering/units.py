"""Unit/lesson outputs — per-lesson Markdown + metadata keyed for Storage (pure).

The worker persists the returned mapping; lessons without renderable content
are skipped (no empty files).
"""

from app.domains.conversion.models import Block, Document, Lesson
from app.domains.conversion.rendering.markdown import render_block


def _index_blocks(doc: Document) -> dict[str, Block]:
    return {block.id: block for page in doc.pages for block in page.blocks}


def _lesson_refs(lesson: Lesson) -> list[str]:
    return [ref for section in lesson.sections for ref in section.block_refs]


def build_unit_outputs(doc: Document, assets_by_id: dict[str, str] | None = None) -> dict[str, str]:
    """Map output-relative keys to text content."""
    resolved = (
        dict(assets_by_id)
        if assets_by_id is not None
        else {asset.id: asset.storage_key for asset in doc.assets}
    )
    index = _index_blocks(doc)
    outputs: dict[str, str] = {}
    for u, unit in enumerate(doc.units, 1):
        prefix = f"units/{u:02d}"
        outputs[f"{prefix}/metadata.json"] = unit.model_dump_json(indent=2)
        for li, lesson in enumerate(unit.lessons, 1):
            wanted = {ref for ref in _lesson_refs(lesson) if ref in index}
            if not wanted:
                continue
            parts = [
                rendered
                for page in sorted(doc.pages, key=lambda p: p.number)
                for block in sorted(page.blocks, key=lambda b: b.order)
                if block.id in wanted
                for rendered in [render_block(block, resolved)]
                if rendered
            ]
            if not parts:
                continue
            lesson_prefix = f"{prefix}/lessons/{li:02d}"
            outputs[f"{lesson_prefix}/content.md"] = "\n\n".join(parts)
            outputs[f"{lesson_prefix}/metadata.json"] = lesson.model_dump_json(indent=2)
    return outputs

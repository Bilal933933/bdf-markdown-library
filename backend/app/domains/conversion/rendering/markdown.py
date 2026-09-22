"""Markdown renderer — Document Model to Markdown (pure, no IO).

Required: block/doc inputs. Optional: assets_by_id (asset_id -> storage_key).
Blocks are the source of truth; stats are derived at render time, never stored.
"""

from app.domains.conversion.models import (
    Block,
    CodePayload,
    ContentStats,
    Document,
    HeadingPayload,
    ImagePayload,
    ListPayload,
    ParagraphPayload,
    QuotePayload,
    TablePayload,
)


def _escape_table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _render_heading(payload: HeadingPayload) -> str:
    text = payload.text.strip()
    return f"{'#' * payload.level} {text}" if text else ""


def _render_list(payload: ListPayload) -> str:
    lines: list[str] = []
    counters: dict[int, int] = {}
    for item in payload.items:
        text = item.text.strip()
        if not text:
            continue
        indent = "  " * item.level
        if payload.ordered:
            counters[item.level] = counters.get(item.level, 0) + 1
            lines.append(f"{indent}{counters[item.level]}. {text}")
        else:
            lines.append(f"{indent}- {text}")
    return "\n".join(lines)


def _render_table(payload: TablePayload) -> str:
    rows = [[_escape_table_cell(cell.text) for cell in row.cells] for row in payload.rows]
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    out = [
        "| " + " | ".join(padded[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    out.extend("| " + " | ".join(row) + " |" for row in padded[1:])
    if payload.fallback_image:
        out.append(f"![]({payload.fallback_image})")
    return "\n".join(out)


def _render_image(payload: ImagePayload, assets_by_id: dict[str, str] | None) -> str:
    key = (assets_by_id or {}).get(payload.asset_id, payload.asset_id)
    out = f"![{payload.alt}]({key})"
    if payload.caption:
        out += f"\n*{payload.caption.strip()}*"
    return out


def _render_quote(payload: QuotePayload) -> str:
    lines = [f"> {line.strip()}" for line in payload.text.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    if payload.attribution and payload.attribution.strip():
        lines.append(f"> — {payload.attribution.strip()}")
    return "\n".join(lines)


def _render_code(payload: CodePayload) -> str:
    lang = payload.language or ""
    return f"```{lang}\n{payload.text}\n```" if payload.text else ""


def render_block(block: Block, assets_by_id: dict[str, str] | None = None) -> str:
    """Render one Block to Markdown. Returns "" for empty content (caller skips)."""
    payload = block.payload
    if isinstance(payload, HeadingPayload):
        return _render_heading(payload)
    if isinstance(payload, ParagraphPayload):
        return payload.text.strip()
    if isinstance(payload, ListPayload):
        return _render_list(payload)
    if isinstance(payload, TablePayload):
        return _render_table(payload)
    if isinstance(payload, ImagePayload):
        return _render_image(payload, assets_by_id)
    if isinstance(payload, QuotePayload):
        return _render_quote(payload)
    if isinstance(payload, CodePayload):
        return _render_code(payload)
    return ""


def collect_stats(doc: Document) -> ContentStats:
    """Count blocks per type across all pages (derived, never stored)."""
    stats = ContentStats()
    for page in doc.pages:
        for block in page.blocks:
            kind = block.payload.kind
            if kind == "paragraph":
                stats.paragraphs += 1
            elif kind == "heading":
                stats.headings += 1
            elif kind == "table":
                stats.tables += 1
            elif kind == "image":
                stats.images += 1
            elif kind == "list":
                stats.lists += 1
            elif kind == "quote":
                stats.quotes += 1
            elif kind == "code":
                stats.code += 1
    return stats


def render_document(doc: Document, assets_by_id: dict[str, str] | None = None) -> str:
    """Render a Document to Markdown; pages by number, blocks by order."""
    resolved = (
        dict(assets_by_id)
        if assets_by_id is not None
        else {asset.id: asset.storage_key for asset in doc.assets}
    )
    parts: list[str] = []
    for page in sorted(doc.pages, key=lambda p: p.number):
        for block in sorted(page.blocks, key=lambda b: b.order):
            rendered = render_block(block, resolved)
            if rendered:
                parts.append(rendered)
    return "\n\n".join(parts)

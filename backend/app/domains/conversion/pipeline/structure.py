"""Structure detection — layout info of one PDF page to typed Blocks.

Scope: detection only. No document reading orchestration, no OCR, no
hierarchy (Unit/Lesson) — those are later layers. Tables are built with
pdfplumber, used here only to construct TablePayload.

Heading heuristic (V1): relatively larger size + at least one of
(bold, short line, visual separation). Levels rank distinct heading
sizes, largest first.
"""

import unicodedata
from io import BytesIO

import pdfplumber
import pymupdf

from app.domains.conversion.models import (
    BBox,
    Block,
    BlockPayload,
    BlockSource,
    BlockType,
    Cell,
    ExtractionMethod,
    HeadingPayload,
    ParagraphPayload,
    Row,
    TablePayload,
)

_MAX_HEADING_CHARS = 120
_SIZE_RATIO = 1.08


def _is_rtl(char: str) -> bool:
    code = ord(char)
    return 0x0590 <= code <= 0x08FF or 0xFB00 <= code <= 0xFDFF or 0xFE70 <= code <= 0xFEFF


def _visual_to_logical(text: str) -> str:
    """Restore logical order of unshaped visual-order extraction.

    Pure RTL lines are fully mirrored in visual order — reversing the whole
    line restores logical text exactly. Mixed lines only get intra-word
    (RTL-run) reversal; full bidi reorder is a later Extraction-quality
    concern.
    """
    if any(_is_rtl(char) for char in text) and not any(
        char.isascii() and char.isalnum() for char in text
    ):
        return text[::-1]
    out: list[str] = []
    run: list[str] = []
    for char in text:
        if _is_rtl(char):
            run.append(char)
        else:
            out.extend(reversed(run))
            run.clear()
            out.append(char)
    out.extend(reversed(run))
    return "".join(out)


def _collect_lines(pdf_page: pymupdf.Page) -> list[dict]:
    lines: list[dict] = []
    for pdf_block in pdf_page.get_text("dict")["blocks"]:
        if pdf_block.get("type", 0) != 0:
            continue
        for line in pdf_block.get("lines", []):
            raw = "".join(span.get("text", "") for span in line.get("spans", ""))
            # PyMuPDF returns unshaped visual order: NFKC-fold, then restore
            # logical order (whole RTL lines, else RTL runs). pdfplumber
            # already returns logical order, so tables use _clean_text only.
            text = _visual_to_logical(_clean_text(raw))
            if not text:
                continue
            spans = line.get("spans", [])
            size = max(span.get("size", 0.0) for span in spans)
            bold = all(bool(span.get("flags", 0) & 16) for span in spans)
            x0, y0, x1, y1 = line["bbox"]
            lines.append({"text": text, "size": size, "bold": bold, "bbox": (x0, y0, x1, y1)})
    lines.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return lines


def _body_size(lines: list[dict]) -> float:
    sizes: dict[float, int] = {}
    for line in lines:
        sizes[line["size"]] = sizes.get(line["size"], 0) + 1
    top = max(sizes.values())
    return min(size for size, count in sizes.items() if count == top)


def _is_heading(line: dict, body_size: float, gap_after: float) -> bool:
    if line["size"] <= body_size * _SIZE_RATIO:
        return False
    line_height = line["bbox"][3] - line["bbox"][1] or 1.0
    short = len(line["text"]) <= _MAX_HEADING_CHARS
    separated = gap_after > line_height * 2.0
    return bool(line["bold"] or short or separated)


def _heading_level(size: float, heading_sizes: list[float]) -> int:
    return min(heading_sizes.index(size) + 1, 6)


def _clean_text(raw: str | None) -> str:
    """NFKC-fold presentation forms and collapse whitespace. No reordering."""
    return " ".join(unicodedata.normalize("NFKC", raw or "").split())


def _extract_tables(pdf_bytes: bytes, page_number: int) -> list[dict]:
    tables: list[dict] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        if page_number >= len(pdf.pages):
            return tables
        for found in pdf.pages[page_number].find_tables() or []:
            extracted = found.extract() or []
            rows = [Row(cells=[Cell(text=_clean_text(cell)) for cell in row]) for row in extracted]
            if rows:
                tables.append({"rows": rows, "bbox": found.bbox})
    return tables


def _line_in_table(line: dict, tables: list[dict]) -> bool:
    x0, y0, x1, y1 = line["bbox"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return any(
        tx0 <= cx <= tx1 and ty0 <= cy <= ty1
        for tx0, ty0, tx1, ty1 in (table["bbox"] for table in tables)
    )


def detect_blocks(
    pdf_page: pymupdf.Page, pdf_bytes: bytes | None = None, source_file: str = ""
) -> list[Block]:
    """Detect typed Blocks of one PyMuPDF page, ordered by reading position."""
    page_no = pdf_page.number + 1
    tables = _extract_tables(pdf_bytes, pdf_page.number) if pdf_bytes is not None else []
    lines = [line for line in _collect_lines(pdf_page) if not _line_in_table(line, tables)]

    body_size = _body_size(lines) if lines else 0.0
    gaps = [
        (lines[i + 1]["bbox"][1] - lines[i]["bbox"][3]) if i + 1 < len(lines) else 0.0
        for i in range(len(lines))
    ]
    flags = [_is_heading(line, body_size, gap) for line, gap in zip(lines, gaps, strict=True)]
    heading_sizes = sorted(
        {line["size"] for line, head in zip(lines, flags, strict=True) if head}, reverse=True
    )

    items: list[tuple[tuple[float, float], dict]] = []
    paragraph: list[dict] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(line["text"] for line in paragraph)
            y0 = min(line["bbox"][1] for line in paragraph)
            x0 = min(line["bbox"][0] for line in paragraph)
            y1 = max(line["bbox"][3] for line in paragraph)
            x1 = max(line["bbox"][2] for line in paragraph)
            items.append(((y0, x0), {"kind": "paragraph", "text": text, "bbox": (x0, y0, x1, y1)}))
            paragraph.clear()

    for line, is_head in zip(lines, flags, strict=True):
        if is_head:
            flush_paragraph()
            x0, y0, x1, y1 = line["bbox"]
            items.append(
                (
                    (y0, x0),
                    {
                        "kind": "heading",
                        "text": line["text"],
                        "level": _heading_level(line["size"], heading_sizes),
                        "bbox": line["bbox"],
                    },
                )
            )
        else:
            paragraph.append(line)
    flush_paragraph()

    for table in tables:
        tx0, ty0, tx1, ty1 = table["bbox"]
        items.append(((ty0, tx0), {"kind": "table", "rows": table["rows"], "bbox": table["bbox"]}))

    items.sort(key=lambda item: (item[0][0], item[0][1]))

    blocks: list[Block] = []
    for order, ((_, _), item) in enumerate(items):
        x0, y0, x1, y1 = item["bbox"]
        source = BlockSource(
            file=source_file,
            pages=[page_no],
            bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
            method=(
                ExtractionMethod.PDFPLUMBER if item["kind"] == "table" else ExtractionMethod.PYMUPDF
            ),
        )
        if item["kind"] == "heading":
            payload: BlockPayload = HeadingPayload(level=item["level"], text=item["text"])
            block_type = BlockType.HEADING
        elif item["kind"] == "table":
            payload = TablePayload(rows=item["rows"])
            block_type = BlockType.TABLE
        else:
            payload = ParagraphPayload(text=item["text"])
            block_type = BlockType.PARAGRAPH
        blocks.append(
            Block(
                id=f"p{page_no}-b{order}",
                type=block_type,
                order=order,
                source=source,
                payload=payload,
            )
        )
    return blocks

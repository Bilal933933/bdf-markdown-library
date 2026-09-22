from app.domains.conversion.models import (
    Asset,
    Block,
    BlockSource,
    BlockType,
    Cell,
    CodePayload,
    Document,
    ExtractionMethod,
    HeadingPayload,
    ImagePayload,
    ListPayload,
    Page,
    ParagraphPayload,
    QuotePayload,
    Row,
    TablePayload,
)
from app.domains.conversion.rendering import collect_stats, render_block, render_document


def make_source(**overrides) -> BlockSource:
    data: dict = {"file": "book.pdf", "pages": [1], "method": ExtractionMethod.PYMUPDF}
    data.update(overrides)
    return BlockSource(**data)


def make_block(order: int, block_type: BlockType, payload, bid: str | None = None) -> Block:
    return Block(
        id=bid or f"p1-b{order}",
        type=block_type,
        order=order,
        source=make_source(),
        payload=payload,
    )


def test_heading_renders_level() -> None:
    block = make_block(0, BlockType.HEADING, HeadingPayload(level=2, text="المبتدأ والخبر"))
    assert render_block(block) == "## المبتدأ والخبر"


def test_paragraph_is_passthrough() -> None:
    block = make_block(0, BlockType.PARAGRAPH, ParagraphPayload(text="نص عربي"))
    assert render_block(block) == "نص عربي"


def test_unordered_list_with_nesting() -> None:
    payload = ListPayload(
        ordered=False, items=[{"text": "أ", "level": 0}, {"text": "ب", "level": 1}]
    )
    assert render_block(make_block(0, BlockType.LIST, payload)) == "- أ\n  - ب"


def test_ordered_list_numbers_continuously() -> None:
    payload = ListPayload(ordered=True, items=[{"text": "أ"}, {"text": "ب"}])
    assert render_block(make_block(0, BlockType.LIST, payload)) == "1. أ\n2. ب"


def test_table_escapes_pipes_and_adds_fallback() -> None:
    payload = TablePayload(
        rows=[
            Row(cells=[Cell(text="مصطلح|أ"), Cell(text="تعريف")]),
            Row(cells=[Cell(text="المبتدأ"), Cell(text="اسم")]),
        ],
        fallback_image="tables/t1.png",
    )
    rendered = render_block(make_block(0, BlockType.TABLE, payload))
    assert "| مصطلح\\|أ | تعريف |" in rendered
    assert "| --- | --- |" in rendered
    assert rendered.endswith("![](tables/t1.png)")


def test_image_resolves_storage_key_and_caption() -> None:
    payload = ImagePayload(asset_id="img-1", alt="شكل", caption="توضيح")
    assert render_block(make_block(0, BlockType.IMAGE, payload), {"img-1": "a/b.png"}) == (
        "![شكل](a/b.png)\n*توضيح*"
    )


def test_quote_with_attribution() -> None:
    payload = QuotePayload(text="العلم نور", attribution="مثل")
    assert render_block(make_block(0, BlockType.QUOTE, payload)) == "> العلم نور\n> — مثل"


def test_code_fences_with_language() -> None:
    payload = CodePayload(language="python", text="x = 1")
    assert render_block(make_block(0, BlockType.CODE, payload)) == "```python\nx = 1\n```"


def test_document_orders_pages_and_blocks_and_skips_empty() -> None:
    empty = make_block(2, BlockType.PARAGRAPH, ParagraphPayload(text="   "), "p1-b1")
    page2 = Page(
        number=2,
        blocks=[make_block(0, BlockType.PARAGRAPH, ParagraphPayload(text="ثانية"), "p2-b0")],
    )
    page1 = Page(
        number=1,
        blocks=[
            make_block(1, BlockType.PARAGRAPH, ParagraphPayload(text="فقرة"), "p1-b0"),
            empty,
            make_block(0, BlockType.HEADING, HeadingPayload(level=1, text="عنوان"), "p1-b2"),
        ],
    )
    doc = Document(id="d1", source_file="book.pdf", pages=[page2, page1])
    assert render_document(doc) == "# عنوان\n\nفقرة\n\nثانية"


def test_collect_stats_counts_each_kind() -> None:
    page = Page(
        number=1,
        blocks=[
            make_block(0, BlockType.HEADING, HeadingPayload(level=1, text="ع"), "p1-b0"),
            make_block(1, BlockType.PARAGRAPH, ParagraphPayload(text="ن"), "p1-b1"),
            make_block(
                2,
                BlockType.TABLE,
                TablePayload(rows=[Row(cells=[Cell(text="أ")])]),
                "p1-b2",
            ),
            make_block(3, BlockType.IMAGE, ImagePayload(asset_id="i"), "p1-b3"),
        ],
    )
    doc = Document(
        id="d1",
        source_file="b.pdf",
        pages=[page],
        assets=[Asset(id="i", storage_key="a/i.png", mime="image/png")],
    )
    stats = collect_stats(doc)
    assert (stats.headings, stats.paragraphs, stats.tables, stats.images) == (1, 1, 1, 1)
    assert render_document(doc) == "# ع\n\nن\n\n| أ |\n| --- |\n\n![](a/i.png)"

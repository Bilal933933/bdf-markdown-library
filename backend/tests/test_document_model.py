import pytest
from pydantic import ValidationError

from app.domains.conversion.models import (
    Asset,
    BBox,
    Block,
    BlockSource,
    BlockType,
    Cell,
    CodePayload,
    Document,
    ExtractionMethod,
    HeadingPayload,
    ImagePayload,
    Lesson,
    ListPayload,
    Page,
    ParagraphPayload,
    QuotePayload,
    Row,
    TablePayload,
    Unit,
    UnitStatus,
)


def make_source(**overrides) -> BlockSource:
    data: dict = {"file": "book.pdf", "pages": [1], "method": ExtractionMethod.PYMUPDF}
    data.update(overrides)
    return BlockSource(**data)


def test_heading_block_builds() -> None:
    block = Block(
        id="p1-b0",
        type=BlockType.HEADING,
        order=0,
        source=make_source(),
        payload=HeadingPayload(level=2, text="المبتدأ والخبر"),
    )
    assert block.payload.level == 2


def test_payload_type_mismatch_is_rejected() -> None:
    with pytest.raises(ValidationError, match="payload kind"):
        Block(
            id="p1-b0",
            type=BlockType.HEADING,
            order=0,
            source=make_source(),
            payload=ParagraphPayload(text="نص"),
        )


def test_heading_level_bounds_are_enforced() -> None:
    with pytest.raises(ValidationError):
        HeadingPayload(level=7, text="x")
    with pytest.raises(ValidationError):
        HeadingPayload(level=0, text="x")


def test_list_requires_items_and_nesting() -> None:
    payload = ListPayload(
        ordered=True, items=[{"text": "أ", "level": 0}, {"text": "ب", "level": 1}]
    )
    assert payload.items[1].level == 1
    with pytest.raises(ValidationError):
        ListPayload(ordered=False, items=[])


def test_table_cell_span_defaults() -> None:
    payload = TablePayload(rows=[Row(cells=[Cell(text="أ", header=True), Cell(text="ب")])])
    assert payload.rows[0].cells[0].header is True
    assert payload.rows[0].cells[1].colspan == 1
    with pytest.raises(ValidationError):
        TablePayload(rows=[])


def test_image_payload_references_asset() -> None:
    payload = ImagePayload(asset_id="img-1", alt="شكل")
    assert payload.caption is None


def test_quote_and_code_payloads() -> None:
    assert QuotePayload(text="نص").attribution is None
    assert CodePayload(language="python", text="x = 1").language == "python"


def test_bbox_corners_are_validated() -> None:
    BBox(x0=0, y0=0, x1=10, y1=10)
    with pytest.raises(ValidationError):
        BBox(x0=10, y0=0, x1=0, y1=10)


def test_source_confidence_bounds() -> None:
    make_source(confidence=0.9)
    with pytest.raises(ValidationError):
        make_source(confidence=1.5)


def test_page_rejects_duplicate_orders_and_ids() -> None:
    def block(order: int, bid: str) -> Block:
        return Block(
            id=bid,
            type=BlockType.PARAGRAPH,
            order=order,
            source=make_source(),
            payload=ParagraphPayload(text="نص"),
        )

    with pytest.raises(ValidationError, match="orders must be unique"):
        Page(number=1, blocks=[block(0, "p1-b0"), block(0, "p1-b1")])
    with pytest.raises(ValidationError, match="ids must be unique"):
        Page(number=1, blocks=[block(0, "p1-b0"), block(1, "p1-b0")])
    with pytest.raises(ValidationError):
        Page(number=0)


def test_unit_defaults_to_unknown_section() -> None:
    unit = Unit(id="u1")
    assert unit.status == UnitStatus.UNKNOWN_SECTION
    assert unit.lessons == []


def test_page_range_end_before_start_is_rejected() -> None:
    with pytest.raises(ValidationError, match="page_range"):
        Lesson(id="l1", page_range=(5, 3))
    assert Lesson(id="l1", page_range=(3, 5)).page_range == (3, 5)


def test_document_assembles_and_counts_pages() -> None:
    asset = Asset(id="img-1", storage_key="a/b.png", mime="image/png", pages=[1])
    page = Page(
        number=1,
        blocks=[
            Block(
                id="p1-b0",
                type=BlockType.PARAGRAPH,
                order=0,
                source=make_source(method=ExtractionMethod.PADDLEOCR),
                payload=ParagraphPayload(text="نص"),
            )
        ],
    )
    doc = Document(id="d1", source_file="book.pdf", pages=[page], assets=[asset])
    assert doc.metadata.page_count == 1
    assert doc.units == []

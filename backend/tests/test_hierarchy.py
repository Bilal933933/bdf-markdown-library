from app.domains.conversion.models import (
    Block,
    BlockSource,
    BlockType,
    Document,
    ExtractionMethod,
    HeadingPayload,
    Page,
    ParagraphPayload,
)
from app.domains.conversion.pipeline.hierarchy import normalize_heading_levels


def make_source() -> BlockSource:
    return BlockSource(file="b.pdf", pages=[1], method=ExtractionMethod.PYMUPDF)


def heading(order: int, level: int, text: str = "عنوان") -> Block:
    return Block(
        id=f"p1-b{order}",
        type=BlockType.HEADING,
        order=order,
        source=make_source(),
        payload=HeadingPayload(level=level, text=text),
    )


def paragraph(order: int) -> Block:
    return Block(
        id=f"p1-p{order}",
        type=BlockType.PARAGRAPH,
        order=order,
        source=make_source(),
        payload=ParagraphPayload(text="نص"),
    )


def levels(doc: Document) -> list[int]:
    out: list[int] = []
    for page in sorted(doc.pages, key=lambda p: p.number):
        for block in sorted(page.blocks, key=lambda b: b.order):
            if isinstance(block.payload, HeadingPayload):
                out.append(block.payload.level)
    return out


def test_jumps_are_clamped() -> None:
    doc = Document(
        id="d1",
        source_file="b.pdf",
        pages=[Page(number=1, blocks=[heading(0, 1), heading(1, 3), heading(2, 2)])],
    )
    assert levels(normalize_heading_levels(doc)) == [1, 2, 2]


def test_first_heading_becomes_level_one() -> None:
    doc = Document(id="d1", source_file="b.pdf", pages=[Page(number=1, blocks=[heading(0, 4)])])
    assert levels(normalize_heading_levels(doc)) == [1]


def test_valid_sequence_is_untouched_and_input_unmutated() -> None:
    doc = Document(
        id="d1",
        source_file="b.pdf",
        pages=[Page(number=1, blocks=[heading(0, 1), paragraph(1), heading(2, 2)])],
    )
    result = normalize_heading_levels(doc)
    assert levels(result) == [1, 2]
    assert levels(doc) == [1, 2]
    assert result.pages[0].blocks[1].payload.text == "نص"


def test_correction_flows_across_pages() -> None:
    doc = Document(
        id="d1",
        source_file="b.pdf",
        pages=[
            Page(number=2, blocks=[heading(0, 3, "ثان")]),
            Page(number=1, blocks=[heading(0, 1, "أول")]),
        ],
    )
    assert levels(normalize_heading_levels(doc)) == [1, 2]

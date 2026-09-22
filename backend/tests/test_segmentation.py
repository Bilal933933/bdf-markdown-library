from app.domains.conversion.models import (
    Block,
    BlockSource,
    BlockType,
    Document,
    ExtractionMethod,
    HeadingPayload,
    Page,
    ParagraphPayload,
    UnitStatus,
)
from app.domains.conversion.pipeline.segment import segment_document


def make_source(page: int) -> BlockSource:
    return BlockSource(file="b.pdf", pages=[page], method=ExtractionMethod.PYMUPDF)


def heading(order: int, page: int, level: int, text: str) -> Block:
    return Block(
        id=f"p{page}-b{order}",
        type=BlockType.HEADING,
        order=order,
        source=make_source(page),
        payload=HeadingPayload(level=level, text=text),
    )


def paragraph(order: int, page: int, text: str = "نص") -> Block:
    return Block(
        id=f"p{page}-p{order}",
        type=BlockType.PARAGRAPH,
        order=order,
        source=make_source(page),
        payload=ParagraphPayload(text=text),
    )


def all_refs(doc: Document) -> set[str]:
    return {
        ref
        for unit in doc.units
        for lesson in unit.lessons
        for section in lesson.sections
        for ref in section.block_refs
    }


def all_ids(doc: Document) -> set[str]:
    return {block.id for page in doc.pages for block in page.blocks}


def test_headings_build_units_lessons_sections() -> None:
    doc = Document(
        id="d1",
        source_file="b.pdf",
        pages=[
            Page(
                number=1,
                blocks=[
                    heading(0, 1, 1, "الوحدة"),
                    heading(1, 1, 2, "درس أول"),
                    paragraph(2, 1, "فقرة أولى"),
                    heading(3, 1, 3, "تعريف"),
                    paragraph(4, 1, "فقرة تعريف"),
                ],
            ),
            Page(number=2, blocks=[heading(0, 2, 2, "درس ثان"), paragraph(1, 2)]),
        ],
    )
    result = segment_document(doc)
    assert len(result.units) == 1
    unit = result.units[0]
    assert (unit.title, unit.status, unit.page_range) == ("الوحدة", UnitStatus.CONFIRMED, (1, 2))
    assert [lesson.title for lesson in unit.lessons] == ["درس أول", "درس ثان"]
    assert all(lesson.status == UnitStatus.CONFIRMED for lesson in unit.lessons)
    first = unit.lessons[0]
    assert [s.heading_snapshot for s in first.sections] == ["", "تعريف"]
    assert first.sections[0].block_refs == ["p1-p2"]
    assert [lesson.page_range for lesson in unit.lessons] == [(1, 1), (2, 2)]
    assert all_refs(result) <= all_ids(result)


def test_preamble_goes_to_unknown_unit() -> None:
    doc = Document(
        id="d1",
        source_file="b.pdf",
        pages=[
            Page(
                number=1,
                blocks=[paragraph(0, 1, "تمهيد"), heading(1, 1, 1, "الوحدة")],
            )
        ],
    )
    result = segment_document(doc)
    assert [u.status for u in result.units] == [UnitStatus.UNKNOWN_SECTION, UnitStatus.CONFIRMED]
    assert result.units[0].lessons[0].sections[0].block_refs == ["p1-p0"]
    assert result.units[1].title == "الوحدة"


def test_no_headings_yields_single_unknown_container() -> None:
    doc = Document(id="d1", source_file="b.pdf", pages=[Page(number=3, blocks=[paragraph(0, 3)])])
    result = segment_document(doc)
    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.status == UnitStatus.UNKNOWN_SECTION
    assert unit.page_range == (3, 3)
    assert unit.lessons[0].sections[0].block_refs == ["p3-p0"]


def test_input_is_unmutated() -> None:
    doc = Document(
        id="d1", source_file="b.pdf", pages=[Page(number=1, blocks=[heading(0, 1, 1, "ع")])]
    )
    assert segment_document(doc).units[0].title == "ع"
    assert doc.units == []

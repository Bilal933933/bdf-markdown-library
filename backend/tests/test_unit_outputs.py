import json

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
from app.domains.conversion.pipeline.segment import segment_document
from app.domains.conversion.rendering import build_unit_outputs


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


def two_lesson_doc() -> Document:
    return segment_document(
        Document(
            id="d1",
            source_file="b.pdf",
            pages=[
                Page(
                    number=1,
                    blocks=[
                        heading(0, 1, 1, "الوحدة"),
                        heading(1, 1, 2, "أول"),
                        paragraph(2, 1, "فقرة أولى"),
                    ],
                ),
                Page(
                    number=2,
                    blocks=[heading(0, 2, 2, "ثان"), paragraph(1, 2, "فقرة ثانية")],
                ),
            ],
        )
    )


def test_builds_lesson_files_in_order() -> None:
    outputs = build_unit_outputs(two_lesson_doc())
    assert sorted(outputs) == [
        "units/01/lessons/01/content.md",
        "units/01/lessons/01/metadata.json",
        "units/01/lessons/02/content.md",
        "units/01/lessons/02/metadata.json",
        "units/01/metadata.json",
    ]
    assert outputs["units/01/lessons/01/content.md"] == "فقرة أولى"
    assert outputs["units/01/lessons/02/content.md"] == "فقرة ثانية"
    assert json.loads(outputs["units/01/lessons/01/metadata.json"])["title"] == "أول"
    assert json.loads(outputs["units/01/metadata.json"])["title"] == "الوحدة"


def test_empty_lesson_is_skipped() -> None:
    doc = segment_document(
        Document(
            id="d1",
            source_file="b.pdf",
            pages=[Page(number=1, blocks=[heading(0, 1, 1, "وحدة بلا دروس")])],
        )
    )
    assert build_unit_outputs(doc) == {
        "units/01/metadata.json": doc.units[0].model_dump_json(indent=2)
    }


def test_no_units_yields_nothing() -> None:
    doc = Document(id="d1", source_file="b.pdf", pages=[])
    assert build_unit_outputs(doc) == {}

import pymupdf

from app.domains.conversion.models import BlockType, ExtractionMethod
from app.domains.conversion.pipeline.structure import detect_blocks


def build_sample_pdf() -> tuple[pymupdf.Page, bytes]:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_font(fontname="arr", fontfile="C:/Windows/Fonts/arial.ttf")
    page.insert_font(fontname="arb", fontfile="C:/Windows/Fonts/arialbd.ttf")
    page.insert_text((72, 72), "الوحدة الأولى", fontname="arb", fontsize=26)
    page.insert_text(
        (72, 150),
        "المبتدأ اسم مرفوع يقع في أول الجملة والخبر يتمم معناه.",
        fontname="arr",
        fontsize=12,
    )
    page.insert_text((72, 220), "تعريف المبتدأ", fontname="arb", fontsize=18)
    x0, top, x1, bottom, mid_x, mid_y = 72.0, 260.0, 400.0, 340.0, 236.0, 300.0
    page.draw_rect(pymupdf.Rect(x0, top, x1, bottom))
    page.draw_line(pymupdf.Point(mid_x, top), pymupdf.Point(mid_x, bottom))
    page.draw_line(pymupdf.Point(x0, mid_y), pymupdf.Point(x1, mid_y))
    page.insert_text((80, 282), "مبتدأ", fontname="arr", fontsize=12)
    page.insert_text((244, 282), "خبر", fontname="arr", fontsize=12)
    page.insert_text((80, 322), "العلم", fontname="arr", fontsize=12)
    page.insert_text((244, 322), "نور", fontname="arr", fontsize=12)
    pdf_bytes = doc.tobytes()
    return page, pdf_bytes


def test_detect_heading_paragraph_heading_table() -> None:
    page, pdf_bytes = build_sample_pdf()
    blocks = detect_blocks(page, pdf_bytes, source_file="test.pdf")

    assert [block.type for block in blocks] == [
        BlockType.HEADING,
        BlockType.PARAGRAPH,
        BlockType.HEADING,
        BlockType.TABLE,
    ]
    assert [block.order for block in blocks] == [0, 1, 2, 3]
    assert [block.id for block in blocks] == ["p1-b0", "p1-b1", "p1-b2", "p1-b3"]
    assert [block.payload.level for block in blocks[:1]] == [1]
    assert [block.payload.level for block in blocks[2:3]] == [2]
    src_text = "المبتدأ اسم مرفوع يقع في أول الجملة والخبر يتمم معناه."
    assert blocks[1].payload.text == src_text
    table = blocks[3].payload
    assert [[cell.text for cell in row.cells] for row in table.rows] == [
        ["مبتدأ", "خبر"],
        ["العلم", "نور"],
    ]


def test_block_sources() -> None:
    page, pdf_bytes = build_sample_pdf()
    blocks = detect_blocks(page, pdf_bytes, source_file="test.pdf")

    for block in blocks:
        assert block.source.pages == [1]
        assert block.source.file == "test.pdf"
        assert block.source.bbox is not None
    assert blocks[0].source.method == ExtractionMethod.PYMUPDF
    assert blocks[3].source.method == ExtractionMethod.PDFPLUMBER


def test_without_pdf_bytes_skips_tables() -> None:
    page, _ = build_sample_pdf()
    blocks = detect_blocks(page)

    assert BlockType.TABLE not in [block.type for block in blocks]

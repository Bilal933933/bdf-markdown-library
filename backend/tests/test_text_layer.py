"""Text-layer extraction (extract/pdf_layer) — ordering, cleanup, gate."""

import pymupdf

from app.domains.conversion.extract import (
    clean_line,
    extract_text_layer,
    find_repeating_lines,
    is_lone_page_number,
    judge_text_layer,
    page_lines,
    row_is_arabic,
)

LRM = chr(0x200E)
RLM = chr(0x200F)
PRES_ALEF = chr(0xFE8D)  # عينة أشكال عرضية

CLEAN = "الدافعية حالة داخلية عند الفرد تولد لديه الطاقة وتوجه السلوك نحو الهدف " * 5


class _FakePage:
    def __init__(self, blocks: list[tuple]) -> None:
        self._blocks = blocks

    def get_text(self, kind: str) -> list[tuple]:
        assert kind == "blocks"
        return self._blocks


def _block(x0: float, y0: float, text: str) -> tuple:
    return (x0, y0, x0 + 100, y0 + 20, text, 0, 0)


def test_row_is_arabic() -> None:
    assert row_is_arabic("الدافعية حالة داخلية") is True
    assert row_is_arabic("hello world") is False
    assert row_is_arabic("123 - ()") is True


def test_page_lines_arabic_row_goes_right_to_left() -> None:
    page = _FakePage([_block(100, 10, "عليكم"), _block(300, 10, "السلام")])
    assert page_lines(page) == ["السلام", "عليكم"]


def test_page_lines_latin_row_goes_left_to_right() -> None:
    page = _FakePage([_block(300, 10, "world"), _block(100, 10, "Hello")])
    assert page_lines(page) == ["Hello", "world"]


def test_page_lines_top_row_first() -> None:
    page = _FakePage([_block(100, 50, "الثاني"), _block(100, 10, "الأول")])
    assert page_lines(page) == ["الأول", "الثاني"]


def test_page_lines_skips_image_blocks() -> None:
    page = _FakePage([(100, 10, 200, 30, "صورة", 0, 1), _block(100, 50, "نص")])
    assert page_lines(page) == ["نص"]


def test_clean_line_strips_bidi_marks() -> None:
    assert clean_line(f"{LRM}-١{RLM}  نص") == "-١ نص"
    assert clean_line("  مسافات   زائدة  ") == "مسافات زائدة"


def test_find_repeating_lines_catches_footer() -> None:
    pages = [["عنوان", "متن", "تذييل مشترك", str(i)] for i in range(4)]
    assert find_repeating_lines(pages, 4) == {"عنوان", "تذييل مشترك"}


def test_find_repeating_lines_ignores_body() -> None:
    pages = [["عنوان", f"متن {i}", "تذييل", "1"] for i in range(4)]
    found = find_repeating_lines(pages, 4)
    assert "متن 0" not in found


def test_is_lone_page_number() -> None:
    assert is_lone_page_number("105") is True
    assert is_lone_page_number("١٠٥") is True
    assert is_lone_page_number("سؤال 105") is False
    assert is_lone_page_number("") is False


def test_judge_accepts_clean_arabic() -> None:
    assert judge_text_layer(CLEAN, CLEAN)["verdict"] == "accept"


def test_judge_short_text() -> None:
    assert judge_text_layer("بسم الله", "بسم الله")["verdict"] == "short"


def test_judge_flags_bidi_bullets() -> None:
    lines = [
        f"{LRM}-١{RLM} هو عملية تكون بين معلم ومتعلم داخل الصف",
        f"{RLM}-٢{LRM} الممارسة والتكرار شرط أساسي لحدوث التعلم",
        "الدافعية حالة داخلية توجه السلوك نحو الهدف المطلوب",
        f"{LRM}-٣{RLM} النضج شرط ضروري لا يحدث التعلم بدونه",
        "المشكلة تحتاج حلا مناسبا يراعي الفروق الفردية",
    ]
    text = ("\n".join(lines) + "\n") * 5
    result = judge_text_layer(text, text)
    assert result["verdict"] == "distorted"
    assert "bidi_marks" in result["reasons"]


def test_judge_flags_split_words() -> None:
    text = ("ذهب ا لطالب إ لى ا لمدرسة صباحا وتعلم ا لدروس مع ا لمعلم " * 5).strip()
    result = judge_text_layer(text, text)
    assert result["verdict"] == "distorted"
    assert "split_words" in result["reasons"]


def test_judge_flags_presentation_forms() -> None:
    text = ((PRES_ALEF + " ") * 90).strip()
    result = judge_text_layer(text, text)
    assert result["verdict"] == "distorted"
    assert "presentation_forms" in result["reasons"]


def test_extract_text_layer_drops_footer_and_page_number(tmp_path) -> None:
    body = "hello world content line for wiring check " * 5
    doc = pymupdf.open()
    for number in range(3):
        page = doc.new_page()
        page.insert_font(fontname="arr", fontfile="C:/Windows/Fonts/arial.ttf")
        page.insert_text((72, 72), "TITLE", fontname="arr", fontsize=16)
        page.insert_text((72, 150), body.strip(), fontname="arr", fontsize=12)
        page.insert_text((72, 750), "TESTFOOT", fontname="arr", fontsize=10)
        page.insert_text((72, 770), str(7 + number), fontname="arr", fontsize=10)
    data = doc.tobytes()
    doc.close()

    pages = extract_text_layer(data)
    assert [p["page"] for p in pages] == [1, 2, 3]
    for p in pages:
        assert "TESTFOOT" not in p["text"]
        assert p["verdict"] in ("accept", "short", "distorted")

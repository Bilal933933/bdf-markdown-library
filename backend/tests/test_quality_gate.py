from app.domains.conversion.models import (
    Block,
    BlockSource,
    BlockType,
    CodePayload,
    ExtractionMethod,
    Page,
    ParagraphPayload,
)
from app.domains.conversion.quality import QualityDecision, analyze_page


def make_page(texts: list[str]) -> Page:
    blocks = [
        Block(
            id=f"p1-b{i}",
            type=BlockType.PARAGRAPH,
            order=i,
            source=BlockSource(file="b.pdf", pages=[1], method=ExtractionMethod.PADDLEOCR),
            payload=ParagraphPayload(text=text),
        )
        for i, text in enumerate(texts)
    ]
    return Page(number=1, blocks=blocks)


GOOD_ARABIC = "المبتدأ اسم مرفوع يقع في أول الجملة والخبر يتمم معناه ويكمل الفائدة للمستمع والقارئ"


def test_good_arabic_page_is_accepted() -> None:
    result = analyze_page(
        make_page([GOOD_ARABIC, "كان وأخواتها أفعال ناسخة ترفع المبتدأ وتنصب الخبر"])
    )
    assert result.decision == QualityDecision.ACCEPT
    assert result.score >= 0.75
    assert result.reasons == []


def test_empty_page_is_retried_with_zero_score() -> None:
    result = analyze_page(make_page([]))
    assert result.score == 0.0
    assert result.decision == QualityDecision.RETRY
    assert result.reasons == ["empty_or_too_short"]


def test_too_short_text_is_retried() -> None:
    result = analyze_page(make_page(["بسم الله"]))
    assert result.decision == QualityDecision.RETRY
    assert result.reasons == ["empty_or_too_short"]


def test_control_chars_drag_score_to_gemini() -> None:
    dirty = GOOD_ARABIC + chr(3) * 30 + chr(4) * 30
    result = analyze_page(make_page([dirty]))
    assert result.decision == QualityDecision.GEMINI
    assert "control_chars" in result.reasons


def test_repeated_text_is_penalized() -> None:
    result = analyze_page(make_page(["الخبر الخبر " * 12]))
    assert "repeated_text" in result.reasons
    assert result.score < 0.75


def test_code_blocks_are_excluded_from_arabic_ratio() -> None:
    page = make_page([GOOD_ARABIC])
    page.blocks.append(
        Block(
            id="p1-b9",
            type=BlockType.CODE,
            order=9,
            source=BlockSource(file="b.pdf", pages=[1], method=ExtractionMethod.PADDLEOCR),
            payload=CodePayload(language="python", text="x = 1\nprint(x)"),
        )
    )
    result = analyze_page(page)
    assert result.decision == QualityDecision.ACCEPT

from app.domains.conversion.models import (
    Block,
    BlockSource,
    BlockType,
    CodePayload,
    ExtractionMethod,
    Page,
    ParagraphPayload,
)
from app.domains.conversion.quality import QualityDecision, analyze_page, get_word_checker


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


SENTENCE_1 = "المبتدأ اسم مرفوع يقع في أول الجملة والخبر يتمم معناه ويكمل الفائدة للمستمع والقارئ"
SENTENCE_2 = "كان وأخواتها أفعال ناسخة ترفع المبتدأ وتنصب الخبر"
LEXICON = frozenset((SENTENCE_1 + " " + SENTENCE_2).split())

GIBBERISH_12 = "غبشقة برطمة هلهلة دندنة وشوشة طمطمة لعلعة قوقعة زمجرة هرولة دحرجة قرقعة"
VOCALIZED_12 = "كِتَابٌ قَلَمٌ بَابٌ نُورٌ عِلْمٌ عَمَلٌ حُبٌّ سَلَامٌ رَحْمَةٌ عَدْلٌ حَقٌّ صِدْقٌ"


def test_default_without_lexicon_keeps_v1_behavior() -> None:
    result = analyze_page(make_page([SENTENCE_1, SENTENCE_2]))
    assert result.decision == QualityDecision.ACCEPT
    assert result.reasons == []


def test_known_words_pass_with_lexicon() -> None:
    result = analyze_page(make_page([SENTENCE_1, SENTENCE_2]), lexicon=LEXICON)
    assert result.decision == QualityDecision.ACCEPT
    assert "camel_oov" not in result.reasons


def test_unknown_words_are_penalized() -> None:
    result = analyze_page(make_page([GIBBERISH_12]), lexicon=LEXICON)
    assert "camel_oov" in result.reasons
    assert result.decision == QualityDecision.RETRY


def test_code_blocks_are_excluded_from_camel() -> None:
    page = make_page([SENTENCE_1])
    page.blocks.append(
        Block(
            id="p1-b9",
            type=BlockType.CODE,
            order=9,
            source=BlockSource(file="b.pdf", pages=[1], method=ExtractionMethod.PADDLEOCR),
            payload=CodePayload(language="text", text=GIBBERISH_12),
        )
    )
    result = analyze_page(page, lexicon=LEXICON)
    assert result.decision == QualityDecision.ACCEPT
    assert "camel_oov" not in result.reasons


def test_diacritic_heavy_page_is_flagged_only() -> None:
    result = analyze_page(make_page([VOCALIZED_12]), lexicon=LEXICON)
    assert "diacritic_suspect" in result.reasons
    assert "camel_oov" in result.reasons
    assert result.decision == QualityDecision.RETRY


def test_few_words_skip_camel() -> None:
    result = analyze_page(make_page(["غبشقة برطمة هلهلة دندنة وشوشة"]), lexicon=LEXICON)
    assert "camel_oov" not in result.reasons
    assert result.decision == QualityDecision.ACCEPT


def test_short_page_keeps_early_exit_with_lexicon() -> None:
    result = analyze_page(make_page(["بسم الله"]), lexicon=LEXICON)
    assert result.decision == QualityDecision.RETRY
    assert result.reasons == ["empty_or_too_short"]


def test_predicate_lexicon_works_like_wordlist() -> None:
    known = lambda word: word in LEXICON  # noqa: E731
    result = analyze_page(make_page([GIBBERISH_12]), lexicon=known)
    assert "camel_oov" in result.reasons
    assert result.decision == QualityDecision.RETRY


def test_checker_disabled_without_path() -> None:
    assert get_word_checker(None) is None
    assert get_word_checker("") is None


def test_checker_disabled_with_missing_file() -> None:
    assert get_word_checker("E:/no/such/morphology.db") is None

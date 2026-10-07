"""PDF text-layer extraction — PyMuPDF blocks in Arabic reading order (pure).

Replaces the deleted _ocr/extract-text.py (pdfjs naive join split words and
leaked bidi marks). Blocks sort top→bottom; within a row right→left when the
row is Arabic-dominant. Bidi marks are stripped, repeated edge lines
(headers/footers) and lone page numbers are dropped, and a quality gate flags
distorted layers (bidi_marks / split_words / presentation_forms / ...) for OCR.
"""

import argparse
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

CHUNK = 40

_CONTROL_RANGES = [(0x00, 0x1F), (0x7F, 0x9F)]
_BIDI_RANGES = [(0x200B, 0x200F), (0x202A, 0x202E), (0x061C, 0x061C), (0xFEFF, 0xFEFF)]
_ARABIC_RANGES = [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)]
_TASHKEEL_RANGES = [(0x064B, 0x065F), (0x0670, 0x0670)]
_DIGIT_RANGES = [(0x30, 0x39), (0x0660, 0x0669)]
_PRES_RANGES = [(0xFB50, 0xFDFF), (0xFE70, 0xFEFF)]
_PAGE_NUM_OK = set("0123456789 \t-()[]")


def _in_ranges(ch: str, ranges: list[tuple[int, int]]) -> bool:
    c = ord(ch)
    return any(lo <= c <= hi for lo, hi in ranges)


def is_arabic_char(ch: str) -> bool:
    return _in_ranges(ch, _ARABIC_RANGES)


def is_letter(ch: str) -> bool:
    return (ch.isascii() and ch.isalpha()) or is_arabic_char(ch)


def strip_special(text: str) -> str:
    """Drop control chars and bidi marks (they leaked into output before)."""
    return "".join(
        ch
        for ch in text
        if not _in_ranges(ch, _CONTROL_RANGES) and not _in_ranges(ch, _BIDI_RANGES)
    )


def count_controls(text: str) -> int:
    return sum(1 for ch in text if _in_ranges(ch, _CONTROL_RANGES))


def count_bidi(text: str) -> int:
    return sum(1 for ch in text if _in_ranges(ch, _BIDI_RANGES))


def remove_tashkeel(word: str) -> str:
    return "".join(ch for ch in word if not _in_ranges(ch, _TASHKEEL_RANGES))


def has_digit(word: str) -> bool:
    return any(_in_ranges(ch, _DIGIT_RANGES) for ch in word)


def row_is_arabic(text: str) -> bool:
    letters = [ch for ch in text if is_letter(ch)]
    if not letters:
        return True
    return sum(1 for ch in letters if is_arabic_char(ch)) / len(letters) >= 0.5


def page_lines(page: "pymupdf.Page") -> list[str]:
    """Raw text lines of one page in Arabic reading order."""
    blocks = [b for b in page.get_text("blocks") if b[4].strip() and b[6] == 0]
    blocks.sort(key=lambda b: (round(b[1], 1), b[0]))
    rows: list[list[tuple]] = []
    for b in blocks:
        for row in rows:
            if abs(b[1] - row[0][1]) <= 5:
                row.append(b)
                break
        else:
            rows.append([b])
    lines: list[str] = []
    for row in rows:
        probe = " ".join(b[4] for b in row)
        ordered = sorted(row, key=lambda b: b[0], reverse=row_is_arabic(probe))
        for b in ordered:
            lines.extend(b[4].splitlines())
    return lines


def clean_line(line: str) -> str:
    return re.sub(r"[ \t]+", " ", strip_special(line)).strip()


def find_repeating_lines(all_lines: list[list[str]], total: int) -> set[str]:
    """Short lines repeating across pages (first line / last two only)."""
    counter: Counter[str] = Counter()
    for lines in all_lines:
        edge = [ln for ln in (lines[:1] + lines[-2:]) if ln and len(ln) < 60]
        counter.update(set(edge))
    return {ln for ln, n in counter.items() if n >= max(3, int(total * 0.1))}


def is_lone_page_number(line: str) -> bool:
    return 0 < len(line) <= 6 and all(
        ch in _PAGE_NUM_OK or _in_ranges(ch, _DIGIT_RANGES) for ch in line
    )


def judge_text_layer(raw: str, cleaned: str) -> dict:
    """Accept / short / distorted + reasons; distorted pages go to OCR."""
    useful = len(re.sub(r"\s+", "", strip_special(cleaned)))
    if useful < 80:
        return {"verdict": "short", "useful": useful, "reasons": []}
    reasons: list[str] = []
    if count_controls(raw) / (useful + 1) > 0.3:
        reasons.append("control_chars")
    lines = [ln for ln in cleaned.splitlines() if ln.strip()]
    if len(lines) >= 5:
        marked = sum(1 for ln in lines if count_bidi(ln) > 0) / len(lines)
        if marked > 0.3:
            reasons.append("bidi_marks")
    letters = [ch for ch in cleaned if is_letter(ch)]
    if len(letters) >= 20:
        if sum(1 for ch in letters if is_arabic_char(ch)) / len(letters) < 0.5:
            reasons.append("low_arabic_ratio")
        if sum(1 for ch in letters if _in_ranges(ch, _PRES_RANGES)) / len(letters) > 0.3:
            reasons.append("presentation_forms")
    lexemes = [w for w in re.split(r"\s+", cleaned) if any(is_letter(ch) for ch in w)]
    bare = ["".join(ch for ch in remove_tashkeel(w) if is_letter(ch)) for w in lexemes]
    bare = [w for w in bare if w]
    if len(bare) >= 10:
        if sum(1 for w in bare if len(w) <= 2) / len(bare) > 0.5:
            reasons.append("fragmented_text")
        if sum(1 for w in bare if len(w) == 1 and is_arabic_char(w)) / len(bare) > 0.25:
            reasons.append("split_words")
        if sum(1 for w in lexemes if has_digit(w)) / len(lexemes) > 0.1:
            reasons.append("mixed_alnum")
    if reasons:
        return {"verdict": "distorted", "useful": useful, "reasons": reasons}
    return {"verdict": "accept", "useful": useful, "reasons": []}


def extract_text_layer(data: bytes, limit: int = 0) -> list[dict]:
    """Pure extraction: PDF bytes → [{page, text}]; distorted pages flagged."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    total = min(limit, doc.page_count) if limit else doc.page_count
    raw_pages = [page_lines(doc[i]) for i in range(total)]
    cleaned_pages = [[c for c in (clean_line(ln) for ln in raw) if c] for raw in raw_pages]
    repeating = find_repeating_lines(cleaned_pages, total)
    pages: list[dict] = []
    for number, lines in enumerate(cleaned_pages, start=1):
        kept = [ln for ln in lines if ln not in repeating and not is_lone_page_number(ln)]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
        verdict = judge_text_layer("\n".join(raw_pages[number - 1]), text)
        if verdict["verdict"] == "distorted":
            text = f"[تعذر استخراج النص من الصفحة {number} — طبقة نصية مشوهة]"
        pages.append({"page": number, "text": text, "verdict": verdict["verdict"]})
    doc.close()
    return pages


def write_part(book_dir: Path, book_name: str, part_index: int, buffer: list[dict]) -> None:
    idx = str(part_index).zfill(2)
    nums = [p["page"] for p in buffer]
    header = f"# {book_name} — الجزء {part_index} (صفحات {min(nums)}-{max(nums)})\n\n"
    body = "\n\n".join(f"## صفحة {p['page']}\n\n{p['text'].strip()}" for p in buffer)
    (book_dir / f"part-{idx}.md").write_text(header + body + "\n", encoding="utf-8")


def _log(msg: str) -> None:
    print(f"[{datetime.now(UTC).isoformat()}] {msg}", flush=True)


def main(argv: list[str] | None = None) -> int:
    """CLI: book name + PDF path → <repo-root>/<book>/part-XX.md (40 pages each)."""
    parser = argparse.ArgumentParser(description="استخراج مباشر للطبقة النصية (PyMuPDF)")
    parser.add_argument("book", help="اسم الكتاب (مجلد الناتج)")
    parser.add_argument("pdf", help="مسار ملف PDF")
    parser.add_argument("total", nargs="?", default="0", help="عدد الصفحات (0 = الكل)")
    args = parser.parse_args(argv)

    book_dir = Path(__file__).resolve().parents[5] / args.book
    book_dir.mkdir(parents=True, exist_ok=True)
    data = Path(args.pdf).read_bytes()
    pages = extract_text_layer(data, int(args.total))
    _log(f"البدء: {len(pages)} صفحة")
    buffer: list[dict] = []
    part_index = 1
    distorted = 0
    for p in pages:
        if p["verdict"] == "distorted":
            distorted += 1
        buffer.append(p)
        if len(buffer) >= CHUNK:
            write_part(book_dir, args.book, part_index, buffer)
            buffer = []
            part_index += 1
        if p["page"] % 25 == 0 or p["page"] == len(pages):
            _log(f"تقدم: {p['page']}/{len(pages)}")
    if buffer:
        write_part(book_dir, args.book, part_index, buffer)
    _log(f"اكتمل الاستخراج — صفحات مشوهة حُوّلت لـOCR: {distorted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

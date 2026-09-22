"""Semantic segmentation — headings to Unit/Lesson/Section references (pure, no IO).

Rule-based V1 over normalized heading levels. Sections reference content blocks
only (heading text lives in snapshot/title); unknown content is labeled
unknown_section, never invented (Rule 1).
"""

from app.domains.conversion.models import (
    Block,
    Document,
    HeadingPayload,
    Lesson,
    Section,
    Unit,
    UnitStatus,
)


class _SectionAcc:
    def __init__(self, snapshot: str = "") -> None:
        self.snapshot = snapshot
        self.refs: list[str] = []
        self.pages: list[int] = []


class _LessonAcc:
    def __init__(self, lid: str, title: str = "", confirmed: bool = False) -> None:
        self.id = lid
        self.title = title
        self.confirmed = confirmed
        self.sections: list[_SectionAcc] = []


class _UnitAcc:
    def __init__(self, uid: str, title: str = "", confirmed: bool = False) -> None:
        self.id = uid
        self.title = title
        self.confirmed = confirmed
        self.lessons: list[_LessonAcc] = []


def _page_range(pages: list[int]) -> tuple[int, int] | None:
    return (min(pages), max(pages)) if pages else None


def _freeze_section(acc: _SectionAcc) -> Section:
    return Section(heading_snapshot=acc.snapshot, block_refs=list(acc.refs))


def _freeze_lesson(acc: _LessonAcc) -> Lesson:
    sections = [_freeze_section(s) for s in acc.sections]
    pages = [p for s in acc.sections for p in s.pages]
    return Lesson(
        id=acc.id,
        title=acc.title,
        page_range=_page_range(pages),
        status=UnitStatus.CONFIRMED if acc.confirmed else UnitStatus.UNKNOWN_SECTION,
        confidence=1.0 if acc.confirmed else 0.0,
        sections=sections,
    )


def _freeze_unit(acc: _UnitAcc) -> Unit:
    lessons = [_freeze_lesson(lesson) for lesson in acc.lessons]
    ranges = [lesson.page_range for lesson in lessons if lesson.page_range is not None]
    pages = [p for start, end in ranges for p in (start, end)]
    return Unit(
        id=acc.id,
        title=acc.title,
        page_range=_page_range(pages),
        status=UnitStatus.CONFIRMED if acc.confirmed else UnitStatus.UNKNOWN_SECTION,
        confidence=1.0 if acc.confirmed else 0.0,
        lessons=lessons,
    )


def segment_document(doc: Document) -> Document:
    """Return a copy with units built from heading structure."""
    result = doc.model_copy(deep=True)
    units: list[_UnitAcc] = []
    unit: _UnitAcc | None = None
    lesson: _LessonAcc | None = None
    section: _SectionAcc | None = None

    def ensure_unit() -> _UnitAcc:
        nonlocal unit, lesson, section
        if unit is None:
            unit = _UnitAcc(uid=f"u{len(units) + 1}")
            units.append(unit)
            lesson = None
            section = None
        assert unit is not None
        return unit

    def ensure_lesson() -> _LessonAcc:
        nonlocal lesson, section
        acc = ensure_unit()
        if lesson is None:
            lesson = _LessonAcc(lid=f"{acc.id}-l{len(acc.lessons) + 1}")
            acc.lessons.append(lesson)
            section = None
        assert lesson is not None
        return lesson

    def ensure_section() -> _SectionAcc:
        nonlocal section
        acc = ensure_lesson()
        if section is None:
            section = _SectionAcc()
            acc.sections.append(section)
        return section

    ordered: list[Block] = [
        block
        for page in sorted(result.pages, key=lambda p: p.number)
        for block in sorted(page.blocks, key=lambda b: b.order)
    ]
    for block in ordered:
        payload = block.payload
        if isinstance(payload, HeadingPayload):
            text = payload.text.strip()
            if payload.level == 1:
                unit = _UnitAcc(uid=f"u{len(units) + 1}", title=text, confirmed=True)
                units.append(unit)
                lesson = None
                section = None
            elif payload.level == 2:
                uacc = ensure_unit()
                lesson = _LessonAcc(
                    lid=f"{uacc.id}-l{len(uacc.lessons) + 1}", title=text, confirmed=True
                )
                uacc.lessons.append(lesson)
                section = None
            else:
                lacc = ensure_lesson()
                section = _SectionAcc(snapshot=text)
                lacc.sections.append(section)
        else:
            section = ensure_section()
            section.refs.append(block.id)
            section.pages.extend(block.source.pages)

    result.units = [_freeze_unit(u) for u in units]
    return result

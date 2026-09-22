import pytest
from pydantic import ValidationError

from app.domains.conversion.models import (
    CheckpointStatus,
    Conversion,
    ConversionStatus,
    PageCheckpoint,
)


def test_conversion_defaults_to_queued() -> None:
    conv = Conversion(id="c1", source_file="book.pdf")
    assert conv.status == ConversionStatus.QUEUED
    assert conv.progress == 0
    assert conv.error is None


def test_legal_transitions() -> None:
    conv = Conversion(id="c1", source_file="book.pdf")
    conv = conv.transition_to(ConversionStatus.PROCESSING)
    assert conv.status == ConversionStatus.PROCESSING
    conv = conv.transition_to(ConversionStatus.FAILED)
    conv = conv.transition_to(ConversionStatus.QUEUED)
    assert conv.status == ConversionStatus.QUEUED
    orphan = Conversion(id="c2", source_file="b.pdf", status=ConversionStatus.PROCESSING)
    assert orphan.transition_to(ConversionStatus.QUEUED).status == ConversionStatus.QUEUED
    partial = Conversion(id="c3", source_file="b.pdf", status=ConversionStatus.PROCESSING)
    partial = partial.transition_to(ConversionStatus.PARTIAL)
    assert partial.transition_to(ConversionStatus.QUEUED).status == ConversionStatus.QUEUED


def test_illegal_transitions_are_rejected() -> None:
    conv = Conversion(id="c1", source_file="book.pdf")
    with pytest.raises(ValueError, match="illegal transition"):
        conv.transition_to(ConversionStatus.COMPLETED)
    done = Conversion(id="c2", source_file="b.pdf", status=ConversionStatus.COMPLETED)
    with pytest.raises(ValueError, match="illegal transition"):
        done.transition_to(ConversionStatus.PROCESSING)
    with pytest.raises(ValueError, match="illegal transition"):
        done.transition_to(ConversionStatus.PARTIAL)


def test_current_page_bounded_by_total() -> None:
    with pytest.raises(ValidationError):
        Conversion(id="c1", source_file="b.pdf", total_pages=10, current_page=11)
    assert Conversion(id="c1", source_file="b.pdf", total_pages=10, current_page=10)


def test_progress_bounds() -> None:
    with pytest.raises(ValidationError):
        Conversion(id="c1", source_file="b.pdf", progress=101)


def test_checkpoint_defaults() -> None:
    cp = PageCheckpoint(conversion_id="c1", page_number=173)
    assert cp.status == CheckpointStatus.PENDING
    assert cp.attempts == 0
    assert cp.method is None
    with pytest.raises(ValidationError):
        PageCheckpoint(conversion_id="c1", page_number=0)

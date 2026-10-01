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


def test_pause_resume_cancel_transitions() -> None:
    processing = Conversion(id="c1", source_file="b.pdf", status=ConversionStatus.PROCESSING)
    assert processing.transition_to(ConversionStatus.PAUSED).status == ConversionStatus.PAUSED
    assert processing.transition_to(ConversionStatus.CANCELLED).status == ConversionStatus.CANCELLED
    paused = Conversion(id="c1", source_file="b.pdf", status=ConversionStatus.PAUSED)
    assert paused.transition_to(ConversionStatus.QUEUED).status == ConversionStatus.QUEUED
    assert paused.transition_to(ConversionStatus.CANCELLED).status == ConversionStatus.CANCELLED
    queued = Conversion(id="c1", source_file="b.pdf")
    assert queued.transition_to(ConversionStatus.PAUSED).status == ConversionStatus.PAUSED
    assert queued.transition_to(ConversionStatus.CANCELLED).status == ConversionStatus.CANCELLED


def test_terminal_states_reject_exit() -> None:
    cancelled = Conversion(id="c1", source_file="b.pdf", status=ConversionStatus.CANCELLED)
    with pytest.raises(ValueError, match="illegal transition"):
        cancelled.transition_to(ConversionStatus.QUEUED)
    completed = Conversion(id="c2", source_file="b.pdf", status=ConversionStatus.COMPLETED)
    with pytest.raises(ValueError, match="illegal transition"):
        completed.transition_to(ConversionStatus.PAUSED)
    with pytest.raises(ValueError, match="illegal transition"):
        completed.transition_to(ConversionStatus.CANCELLED)


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

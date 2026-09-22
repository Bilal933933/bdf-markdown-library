import shutil

import pymupdf
import pytest
from rq import Queue, SimpleWorker

from app.core.config import get_settings
from app.domains.conversion.models import ConversionStatus
from app.domains.conversion.pipeline.process import QUEUE_NAME, queue_conversion
from app.domains.conversion.services.conversions import create_conversion
from app.infrastructure.database import (
    Base,
    ConversionRow,
    PageCheckpointRow,
    get_engine,
    get_session_factory,
)
from app.infrastructure.redis import get_redis, ping, reset_redis


def build_pdf() -> bytes:
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
    return doc.tobytes()


@pytest.fixture()
def live_queue() -> Queue:
    if not ping():
        pytest.skip("Redis not running")
    reset_redis()
    conn = get_redis()
    conn.flushdb()
    try:
        yield Queue(QUEUE_NAME, connection=conn)
    finally:
        conn.flushdb()
        reset_redis()


def test_queue_conversion_returns_true_live(live_queue: Queue) -> None:
    assert queue_conversion("probe-id") is True
    assert live_queue.count == 1


def test_burst_worker_completes_conversion(live_queue: Queue) -> None:
    from app.infrastructure.storage import LocalStorage

    settings = get_settings()
    Base.metadata.create_all(get_engine())
    db = get_session_factory()()
    storage = LocalStorage(settings.storage_dir)
    conversion = create_conversion(db, storage, "book.pdf", build_pdf(), settings)
    db.close()
    try:
        assert queue_conversion(conversion.id) is True
        worker = SimpleWorker([live_queue], connection=live_queue.connection)
        worker.work(burst=True)
        check = get_session_factory()()
        try:
            row = check.get(ConversionRow, conversion.id)
            assert row is not None
            assert row.status == ConversionStatus.COMPLETED.value
        finally:
            check.close()
        assert (settings.storage_dir / conversion.id / "output" / "document.md").is_file()
    finally:
        cleanup = get_session_factory()()
        try:
            cleanup.query(PageCheckpointRow).filter_by(conversion_id=conversion.id).delete()
            cleanup.query(ConversionRow).filter_by(id=conversion.id).delete()
            cleanup.commit()
        finally:
            cleanup.close()
        shutil.rmtree(settings.storage_dir / conversion.id, ignore_errors=True)

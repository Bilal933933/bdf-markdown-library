import shutil
from pathlib import Path

import pymupdf
import pytest
from rq import Queue, SimpleWorker

from app.core.config import get_settings
from app.domains.conversion.models import ConversionStatus
from app.domains.conversion.pipeline.process import (
    QUEUE_NAME,
    enqueue_missing_jobs,
    queue_conversion,
)
from app.domains.conversion.services.conversions import create_conversion
from app.infrastructure.database import (
    Base,
    ConversionRow,
    PageCheckpointRow,
    get_engine,
    get_session_factory,
)
from app.infrastructure.redis import ping, reset_redis


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


def _server_major() -> int:
    """Major version of the local Redis server (0 when unreachable)."""
    from app.infrastructure.redis import get_redis

    try:
        version = str(get_redis().info("server").get("redis_version", "0"))
        return int(version.split(".")[0])
    except Exception:
        return 0


@pytest.fixture()
def live_queue(monkeypatch: pytest.MonkeyPatch) -> Queue:
    if not ping():
        pytest.skip("Redis not running")
    if _server_major() < 4:
        pytest.skip("Redis >= 4 required (RQ uses multi-field HSET)")
    reset_redis()
    import redis

    scratch = redis.Redis.from_url("redis://127.0.0.1:6379/15", protocol=2)
    scratch.flushdb()
    monkeypatch.setattr(
        "app.domains.conversion.pipeline.process.get_redis", lambda settings=None: scratch
    )
    try:
        yield Queue(QUEUE_NAME, connection=scratch)
    finally:
        scratch.flushdb()
        scratch.close()
        reset_redis()


def test_queue_conversion_returns_true_live(live_queue: Queue) -> None:
    assert queue_conversion("probe-id") is True
    assert live_queue.count == 1


def test_worker_runs_without_fork() -> None:
    import app.worker as worker_module

    assert worker_module.Worker.__name__ == "SimpleWorker"


def queued_job_ids(queue: Queue) -> list[str]:
    ids: list[str] = []
    for job_id in queue.job_ids:
        job = queue.fetch_job(job_id)
        if job is not None and job.args:
            ids.append(str(job.args[0]))
    return ids


def test_missing_jobs_are_enqueued_once(live_queue: Queue, tmp_path: Path) -> None:
    from app.infrastructure.storage import LocalStorage

    settings = get_settings()
    Base.metadata.create_all(get_engine())
    db = get_session_factory()()
    conversion = create_conversion(db, LocalStorage(tmp_path), "b.pdf", build_pdf(), settings)
    try:
        assert enqueue_missing_jobs(db, stale_after_seconds=0) >= 1
        assert conversion.id in queued_job_ids(live_queue)
        before = live_queue.count
        enqueue_missing_jobs(db, stale_after_seconds=0)
        assert live_queue.count == before
    finally:
        db.query(PageCheckpointRow).filter_by(conversion_id=conversion.id).delete()
        db.query(ConversionRow).filter_by(id=conversion.id).delete()
        db.commit()
        db.close()


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

"""RQ worker entrypoint — run with `uv run python -m app.worker`.

Needs Postgres and Redis. Re-queues orphan PROCESSING conversions, then listens.
"""

import logging

from rq import Worker

from app.domains.conversion.pipeline.process import QUEUE_NAME, requeue_orphans
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.redis import get_redis

logger = logging.getLogger(__name__)


def main() -> None:
    db = get_session_factory()()
    try:
        orphans = requeue_orphans(db)
    finally:
        db.close()
    logger.info("requeued %d orphan conversions", orphans)
    Worker([QUEUE_NAME], connection=get_redis()).work()


if __name__ == "__main__":
    main()

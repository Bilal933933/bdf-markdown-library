"""Session lifecycle — one Session per use, always closed.

Required: none. Optional: none (dependency yields Session).
"""

from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.engine import get_engine


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a Session and guarantee close."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()

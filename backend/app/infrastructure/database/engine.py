"""Engine factory — built lazily from Settings, never at import time.

Required: none. Optional: none (module functions take Settings).
"""

from sqlalchemy import Engine, create_engine

from app.core.config import Settings, get_settings

_engine: Engine | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    """Build (once) and return the sync Engine. Raises if DATABASE_URL is missing."""
    global _engine
    if _engine is not None:
        return _engine
    resolved = settings or get_settings()
    if resolved.database_url is None:
        raise ValueError("DATABASE_URL is not configured")
    _engine = create_engine(
        str(resolved.database_url),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )
    return _engine


def reset_engine() -> None:
    """Drop the cached engine (tests / shutdown)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None

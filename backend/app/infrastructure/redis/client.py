"""Redis client — lazy, optional, never mandatory until the worker arrives.

Not wired to /health: unconfigured Redis is "not needed yet", not "down".
Required: none. Optional: none (module functions take Settings).
"""

import redis

from app.core.config import Settings, get_settings

_client: redis.Redis | None = None


def get_redis(settings: Settings | None = None) -> redis.Redis:
    """Build (once) and return the client. Raises if REDIS_URL is missing."""
    global _client
    if _client is not None:
        return _client
    resolved = settings or get_settings()
    if resolved.redis_url is None:
        raise ValueError("REDIS_URL is not configured")
    _client = redis.Redis.from_url(
        str(resolved.redis_url),
        socket_connect_timeout=3,
        protocol=2,  # local Windows port is Redis 5 (no RESP3 HELLO)
    )
    return _client


def ping(settings: Settings | None = None) -> bool:
    """Return True if the server answers, False otherwise — never raise."""
    try:
        return bool(get_redis(settings).ping())
    except Exception:
        return False


def reset_redis() -> None:
    """Drop the cached client (tests / shutdown)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None

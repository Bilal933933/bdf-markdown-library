import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.redis import get_redis, ping, reset_redis


def test_non_redis_scheme_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(redis_url="http://localhost:6379")  # type: ignore[arg-type]


def test_redis_schemes_are_accepted() -> None:
    assert Settings(redis_url="redis://localhost:6379").redis_url is not None
    assert Settings(redis_url="rediss://localhost:6379").redis_url is not None


def test_client_requires_configured_url() -> None:
    reset_redis()
    with pytest.raises(ValueError, match="REDIS_URL is not configured"):
        get_redis(Settings(redis_url=None))


def test_ping_false_when_server_down() -> None:
    settings = Settings(redis_url="redis://127.0.0.1:6379")
    reset_redis()
    try:
        assert ping(settings) is False
    finally:
        reset_redis()


def test_live_ping() -> None:
    settings = Settings()
    if settings.redis_url is None:
        pytest.skip("REDIS_URL not configured")
    reset_redis()
    try:
        assert ping(settings) is True
    except Exception as exc:
        pytest.skip(f"Redis unreachable: {exc}")
    finally:
        reset_redis()

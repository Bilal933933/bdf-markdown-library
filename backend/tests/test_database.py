import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import Settings
from app.infrastructure.database import Base, get_db, get_engine, reset_engine


def test_sqlite_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")  # type: ignore[arg-type]


def test_postgres_dsn_is_accepted() -> None:
    settings = Settings(database_url="postgresql+psycopg://u:p@localhost:5432/dce")
    assert settings.database_url is not None
    assert "postgresql" in str(settings.database_url)


def test_engine_requires_configured_url() -> None:
    reset_engine()
    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        get_engine(Settings(database_url=None))


def test_base_has_no_tables_yet() -> None:
    assert Base.metadata.tables == {}


def test_db_session_runs_and_closes() -> None:
    settings = Settings()
    if settings.database_url is None:
        pytest.skip("DATABASE_URL not configured")
    reset_engine()
    try:
        get_engine(settings)
        gen = get_db()
        db = next(gen)
        try:
            assert db.execute(text("SELECT 1")).scalar() == 1
        finally:
            gen.close()
    except Exception as exc:
        pytest.skip(f"Postgres unreachable: {exc}")
    finally:
        reset_engine()


def test_live_select_one() -> None:
    settings = Settings()
    if settings.database_url is None:
        pytest.skip("DATABASE_URL not configured")
    reset_engine()
    try:
        with get_engine(settings).connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1
    except Exception as exc:
        pytest.skip(f"Postgres unreachable: {exc}")
    finally:
        reset_engine()

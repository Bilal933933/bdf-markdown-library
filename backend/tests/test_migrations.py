import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def alembic_sql(*args: str) -> str:
    env = {**os.environ, "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/dummy"}
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_upgrade_sql_creates_both_tables() -> None:
    sql = alembic_sql("upgrade", "head", "--sql")
    assert "CREATE TABLE conversions" in sql
    assert "CREATE TABLE page_checkpoints" in sql
    assert "ADD COLUMN heartbeat_at" in sql
    assert "ADD COLUMN created_at" in sql


def test_downgrade_sql_drops_both_tables() -> None:
    sql = alembic_sql("downgrade", "head:base", "--sql")
    assert "DROP TABLE page_checkpoints" in sql
    assert "DROP TABLE conversions" in sql

"""Test isolation — migrate TEST_DATABASE_URL to head and point the app at it.

Without it the suite shares the dev database and collides with live work
(stolen orphans, phantom rows). Create once, then run isolated with:
psql ... -c "CREATE DATABASE dce_test"
TEST_DATABASE_URL=postgresql+psycopg://postgres:12345678@127.0.0.1:5432/dce_test
"""

import os
from pathlib import Path

if os.environ.get("TEST_DATABASE_URL"):
    from alembic.config import Config

    from alembic import command

    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    BACKEND = Path(__file__).resolve().parent.parent
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")

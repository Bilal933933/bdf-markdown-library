"""Track originals, outputs, and request linkage (mirrors tables.py)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _bind_columns(table: str) -> set[str]:
    bind = op.get_bind()
    try:
        from sqlalchemy import inspect as sa_inspect

        return {c["name"] for c in sa_inspect(bind).get_columns(table)}
    except Exception:  # offline --sql (MockConnection): assume a fresh database
        return set()


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    try:
        from sqlalchemy import inspect as sa_inspect

        return name in sa_inspect(bind).get_table_names()
    except Exception:  # offline --sql (MockConnection): assume a fresh database
        return False


def upgrade() -> None:
    existing = _bind_columns("conversions")
    if "source_key" not in existing:
        op.add_column("conversions", sa.Column("source_key", sa.String(1024), nullable=True))
    if "source_sha256" not in existing:
        op.add_column("conversions", sa.Column("source_sha256", sa.String(64), nullable=True))
    if "source_size" not in existing:
        op.add_column(
            "conversions",
            sa.Column("source_size", sa.Integer(), nullable=False, server_default="0"),
        )
    if "source_mime" not in existing:
        op.add_column("conversions", sa.Column("source_mime", sa.String(128), nullable=True))
    if "request_id" not in _bind_columns("conversion_events"):
        op.add_column("conversion_events", sa.Column("request_id", sa.String(64), nullable=True))
    if not _has_table("artifacts"):
        op.create_table(
            "artifacts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("conversion_id", sa.String(64), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("key", sa.String(1024), nullable=False),
            sa.Column("sha256", sa.String(64), nullable=True),
            sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mime", sa.String(128), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    if _has_table("artifacts"):
        op.drop_table("artifacts")
    existing = _bind_columns("conversion_events")
    if "request_id" in existing:
        op.drop_column("conversion_events", "request_id")
    existing = _bind_columns("conversions")
    for column in ("source_mime", "source_size", "source_sha256", "source_key"):
        if column in existing:
            op.drop_column("conversions", column)

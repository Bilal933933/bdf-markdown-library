"""Initial tables: conversions, page_checkpoints (mirrors tables.py)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_file", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column("current_page", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(2048), nullable=True),
    )
    op.create_table(
        "page_checkpoints",
        sa.Column("conversion_id", sa.String(64), primary_key=True),
        sa.Column("page_number", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("method", sa.String(16), nullable=True),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("page_checkpoints")
    op.drop_table("conversions")

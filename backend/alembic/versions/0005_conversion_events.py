"""Add conversion_events log (replaces terminal watching)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversion_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("method", sa.String(16), nullable=True),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("note", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("conversion_events")

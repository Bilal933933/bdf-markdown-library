"""Add note to page_checkpoints (skip reasons)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("page_checkpoints", sa.Column("note", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("page_checkpoints", "note")

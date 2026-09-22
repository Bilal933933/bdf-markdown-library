"""Add heartbeat_at to conversions (worker lease)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversions", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("conversions", "heartbeat_at")

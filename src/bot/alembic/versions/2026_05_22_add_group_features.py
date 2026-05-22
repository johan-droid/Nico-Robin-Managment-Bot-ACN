"""Add group_features table.

Revision ID: 2026_05_22_add_group_features
Revises: 2026_05_12_add_nightmode_enabled
Create Date: 2026-05-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.bot.alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_05_22_add_group_features"
down_revision: str | None = "8q1mpw1tzp4y"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "group_features",
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_name", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "feature_name"),
    )


def downgrade() -> None:
    op.drop_table("group_features")
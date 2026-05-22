"""Add point transaction idempotency and last-earned tracking.

Revision ID: 2026_05_22_add_point_transaction_uid_and_last_earned
Revises: 2026_05_22_add_group_features
Create Date: 2026-05-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.bot.alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_05_22_add_point_transaction_uid_and_last_earned"
down_revision: str | None = "2026_05_22_add_group_features"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_points",
        sa.Column("last_earned", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "point_transactions",
        sa.Column("transaction_uid", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_point_transactions_transaction_uid",
        "point_transactions",
        ["transaction_uid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_point_transactions_transaction_uid", table_name="point_transactions")
    op.drop_column("point_transactions", "transaction_uid")
    op.drop_column("user_points", "last_earned")

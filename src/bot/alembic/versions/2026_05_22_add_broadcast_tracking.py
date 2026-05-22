"""Add broadcast tracking tables.

Revision ID: 2026_05_22_add_broadcast_tracking
Revises: 2026_05_22_add_point_transaction_uid_and_last_earned
Create Date: 2026-05-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.bot.alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_05_22_add_broadcast_tracking"
down_revision: str | None = "2026_05_22_add_point_transaction_uid_and_last_earned"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "broadcast_channel_state",
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_forwarded_message_id", sa.Integer(), nullable=True),
        sa.Column("last_forwarded_at", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("channel_id"),
    )

    op.create_table(
        "broadcast_deliveries",
        sa.Column("delivery_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_channel_id", sa.BigInteger(), nullable=False),
        sa.Column("source_message_id", sa.BigInteger(), nullable=False),
        sa.Column("destination_group_id", sa.BigInteger(), nullable=False),
        sa.Column("destination_message_id", sa.Integer(), nullable=False),
        sa.Column(
            "destination_message_kind",
            sa.String(length=20),
            nullable=False,
            server_default="text",
        ),
        sa.ForeignKeyConstraint(
            ["destination_group_id"], ["groups.group_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("delivery_id"),
        sa.UniqueConstraint(
            "source_channel_id",
            "source_message_id",
            "destination_group_id",
        ),
    )

    op.create_index(
        "ix_broadcast_deliveries_source_channel_id",
        "broadcast_deliveries",
        ["source_channel_id"],
    )
    op.create_index(
        "ix_broadcast_deliveries_source_message_id",
        "broadcast_deliveries",
        ["source_message_id"],
    )
    op.create_index(
        "ix_broadcast_deliveries_destination_group_id",
        "broadcast_deliveries",
        ["destination_group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_deliveries_destination_group_id", table_name="broadcast_deliveries")
    op.drop_index("ix_broadcast_deliveries_source_message_id", table_name="broadcast_deliveries")
    op.drop_index("ix_broadcast_deliveries_source_channel_id", table_name="broadcast_deliveries")
    op.drop_table("broadcast_deliveries")
    op.drop_table("broadcast_channel_state")

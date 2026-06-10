"""Merge Alembic heads and add welcome DM fields.

Revision ID: 2026_05_27_merge_heads_add_welcome_dm
Revises: 2026_05_22_add_broadcast_tracking, 2026_05_22_security
Create Date: 2026-05-27 13:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_05_27_merge_heads_add_welcome_dm"
down_revision: str | Sequence[str] | None = (
    "2026_05_22_add_broadcast_tracking",
    "2026_05_22_security",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("groups", "welcome_dm_text"):
        op.add_column("groups", sa.Column("welcome_dm_text", sa.Text(), nullable=True))

    if not _column_exists("groups", "welcome_dm_enabled"):
        op.add_column(
            "groups",
            sa.Column(
                "welcome_dm_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    if _column_exists("groups", "welcome_dm_enabled"):
        op.drop_column("groups", "welcome_dm_enabled")

    if _column_exists("groups", "welcome_dm_text"):
        op.drop_column("groups", "welcome_dm_text")

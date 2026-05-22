"""Add security audit table and soft-delete columns

Revision ID: 2026_05_22_security
Revises: 8q1mpw1tzp4y
Create Date: 2026-05-22 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.bot.alembic import op

revision: str = "2026_05_22_security"
down_revision: str | None = "8q1mpw1tzp4y"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_audit",
        sa.Column("audit_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("group_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        op.f("ix_security_audit_event_type"),
        "security_audit",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_audit_group_id"),
        "security_audit",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_audit_target_id"),
        "security_audit",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_audit_user_id"),
        "security_audit",
        ["user_id"],
        unique=False,
    )

    for table_name in (
        "users",
        "warns",
        "notes",
        "member_profiles",
        "loyalty_points",
        "user_points",
        "flirting_stats",
    ):
        op.add_column(
            table_name,
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    for table_name in (
        "flirting_stats",
        "user_points",
        "loyalty_points",
        "member_profiles",
        "notes",
        "warns",
        "users",
    ):
        op.drop_column(table_name, "deleted_at")

    op.drop_index(op.f("ix_security_audit_user_id"), table_name="security_audit")
    op.drop_index(op.f("ix_security_audit_target_id"), table_name="security_audit")
    op.drop_index(op.f("ix_security_audit_group_id"), table_name="security_audit")
    op.drop_index(op.f("ix_security_audit_event_type"), table_name="security_audit")
    op.drop_table("security_audit")

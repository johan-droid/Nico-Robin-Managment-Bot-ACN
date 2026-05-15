"""Comprehensive migration for all new features - clean database setup

Revision ID: 2024_01_10_comprehensive_feature_migration
Revises: base
Create Date: 2024-01-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2024_01_10_comprehensive_feature_migration"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all new feature tables with clean structure"""

    # Create feature management tables
    _create_feature_management_tables()

    # Create flirting system tables
    _create_flirting_system_tables()

    # Create bot friendship system tables
    _create_bot_friendship_tables()

    # Create point system tables
    _create_point_system_tables()

    # Create managed channels table
    _create_managed_channels_table()

    # Create member profiles table
    _create_member_profiles_table()

    # Create all indexes and constraints
    _create_indexes_and_constraints()


def _create_feature_management_tables() -> None:
    """Create feature toggle and management tables"""

    # Create feature_toggles table
    op.create_table(
        "feature_toggles",
        sa.Column("toggle_id", sa.Integer(), nullable=False),
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
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_name", sa.String(length=100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("enabled_by", sa.BigInteger(), nullable=True),
        sa.Column("enabled_at", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["enabled_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("toggle_id"),
        sa.UniqueConstraint("group_id", "feature_name"),
    )

    # Create feature_permissions table
    op.create_table(
        "feature_permissions",
        sa.Column("permission_id", sa.Integer(), nullable=False),
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
        sa.Column("feature_name", sa.String(length=100), nullable=False),
        sa.Column("user_role", sa.String(length=20), nullable=False),
        sa.Column("can_use", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("permission_id"),
        sa.UniqueConstraint("feature_name", "user_role"),
    )

    # Create feature_usage table
    op.create_table(
        "feature_usage",
        sa.Column("usage_id", sa.Integer(), nullable=False),
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
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("feature_name", sa.String(length=100), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("usage_id"),
        sa.UniqueConstraint("group_id", "user_id", "feature_name"),
    )

    # Create feature_logs table
    op.create_table(
        "feature_logs",
        sa.Column("log_id", sa.Integer(), nullable=False),
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
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("feature_name", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("previous_state", sa.Boolean(), nullable=True),
        sa.Column("new_state", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("log_id"),
    )


def _create_flirting_system_tables() -> None:
    """Create flirting system tables"""

    # Create flirting_attempts table
    op.create_table(
        "flirting_attempts",
        sa.Column("attempt_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.String(length=50), nullable=False),
        sa.Column("attempt_time", sa.BigInteger(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("points_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_given", sa.Text(), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("attempt_id"),
        sa.UniqueConstraint("user_id", "group_id", "event_id", "attempt_time"),
    )

    # Create flirting_stats table
    op.create_table(
        "flirting_stats",
        sa.Column("stats_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "successful_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("favorite_category", sa.String(length=30), nullable=True),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("stats_id"),
        sa.UniqueConstraint("user_id", "group_id"),
    )

    # Create flirting_achievements table
    op.create_table(
        "flirting_achievements",
        sa.Column("achievement_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("achievement_type", sa.String(length=50), nullable=False),
        sa.Column("achievement_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("earned_at", sa.BigInteger(), nullable=False),
        sa.Column("points_reward", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("achievement_id"),
        sa.UniqueConstraint("user_id", "group_id", "achievement_type"),
    )

    # Create flirting_relationships table
    op.create_table(
        "flirting_relationships",
        sa.Column("relationship_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "relationship_level",
            sa.String(length=20),
            nullable=False,
            server_default="stranger",
        ),
        sa.Column("affection_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "interactions_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_interaction", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("relationship_id"),
        sa.UniqueConstraint("user_id", "group_id"),
    )

    # Create flirting_gifts table
    op.create_table(
        "flirting_gifts",
        sa.Column("gift_id", sa.Integer(), nullable=False),
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
        sa.Column("from_user_id", sa.BigInteger(), nullable=True),
        sa.Column("to_user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("gift_type", sa.String(length=30), nullable=False),
        sa.Column("gift_name", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("points_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["from_user_id"], ["users.user_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("gift_id"),
    )

    # Create flirting_preferences table
    op.create_table(
        "flirting_preferences",
        sa.Column("preference_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("preferred_style", sa.String(length=30), nullable=True),
        sa.Column("blocked_categories", sa.Text(), nullable=True),
        sa.Column("auto_respond", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("preference_id"),
        sa.UniqueConstraint("user_id", "group_id"),
    )


def _create_bot_friendship_tables() -> None:
    """Create bot friendship system tables"""

    # Create bot_friendships table
    op.create_table(
        "bot_friendships",
        sa.Column("friendship_id", sa.Integer(), nullable=False),
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
        sa.Column("companion_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("companion_bot_username", sa.String(length=255), nullable=False),
        sa.Column("companion_bot_name", sa.String(length=255), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "friendship_level",
            sa.String(length=20),
            nullable=False,
            server_default="acquaintance",
        ),
        sa.Column("friendship_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("bonded_at", sa.BigInteger(), nullable=False),
        sa.Column("last_interaction", sa.BigInteger(), nullable=False),
        sa.Column(
            "interaction_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("shared_memories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inside_jokes", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("friendship_id"),
        sa.UniqueConstraint("companion_bot_id", "group_id"),
    )

    # Create bot_interactions table
    op.create_table(
        "bot_interactions",
        sa.Column("interaction_id", sa.Integer(), nullable=False),
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
        sa.Column("companion_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("interaction_type", sa.String(length=30), nullable=False),
        sa.Column("trigger_message", sa.Text(), nullable=True),
        sa.Column("nico_response", sa.Text(), nullable=True),
        sa.Column("companion_response", sa.Text(), nullable=True),
        sa.Column(
            "interaction_score", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "friendship_points", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("interaction_time", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("interaction_id"),
    )

    # Create bot_memories table
    op.create_table(
        "bot_memories",
        sa.Column("memory_id", sa.Integer(), nullable=False),
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
        sa.Column("companion_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("memory_type", sa.String(length=30), nullable=False),
        sa.Column("memory_title", sa.String(length=255), nullable=False),
        sa.Column("memory_content", sa.Text(), nullable=False),
        sa.Column("participants", sa.Text(), nullable=True),
        sa.Column("memory_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("memory_time", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("memory_id"),
    )

    # Create bot_gifts table
    op.create_table(
        "bot_gifts",
        sa.Column("gift_id", sa.Integer(), nullable=False),
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
        sa.Column("from_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("to_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("gift_type", sa.String(length=30), nullable=False),
        sa.Column("gift_name", sa.String(length=100), nullable=False),
        sa.Column("gift_description", sa.Text(), nullable=True),
        sa.Column("gift_emoji", sa.String(length=10), nullable=False),
        sa.Column("gift_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("gift_time", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("gift_id"),
    )

    # Create bot_conversations table
    op.create_table(
        "bot_conversations",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
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
        sa.Column("companion_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("conversation_topic", sa.String(length=255), nullable=False),
        sa.Column("conversation_type", sa.String(length=30), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "conversation_score", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("started_at", sa.BigInteger(), nullable=False),
        sa.Column("last_message_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id"),
        task_track_started=True,
        broker_connection_retry_on_startup=True,
    )

    # Create bot_emotions table
    op.create_table(
        "bot_emotions",
        sa.Column("emotion_id", sa.Integer(), nullable=False),
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
        sa.Column("companion_bot_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("emotion_type", sa.String(length=30), nullable=False),
        sa.Column(
            "emotion_intensity", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("emotion_trigger", sa.Text(), nullable=True),
        sa.Column("nico_expression", sa.Text(), nullable=True),
        sa.Column("companion_expression", sa.Text(), nullable=True),
        sa.Column("emotion_time", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("emotion_id"),
    )


def _create_point_system_tables() -> None:
    """Create point system tables"""

    # Create user_points table
    op.create_table(
        "user_points",
        sa.Column("points_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("current_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("experience", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity", sa.BigInteger(), nullable=False),
        sa.Column("selected_apploid", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("points_id"),
        sa.UniqueConstraint("user_id", "group_id"),
    )

    # Create point_transactions table
    op.create_table(
        "point_transactions",
        sa.Column("transaction_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_before", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transaction_time", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("transaction_id"),
    )

    # Create apploids table
    op.create_table(
        "apploids",
        sa.Column("apploid_id", sa.Integer(), nullable=False),
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
        sa.Column("apploid_name", sa.String(length=50), nullable=False, unique=True),
        sa.Column("apploid_emoji", sa.String(length=10), nullable=False),
        sa.Column("apploid_image", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rarity", sa.String(length=20), nullable=False),
        sa.Column("required_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("required_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_limited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_owners", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("apploid_id"),
    )

    # Create user_apploids table
    op.create_table(
        "user_apploids",
        sa.Column("user_apploid_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("apploid_id", sa.Integer(), nullable=False),
        sa.Column("is_equipped", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("purchase_price", sa.Integer(), nullable=False),
        sa.Column("acquired_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["apploid_id"], ["apploids.apploid_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_apploid_id"),
        sa.UniqueConstraint("user_id", "group_id", "apploid_id"),
    )

    # Create point_rewards table
    op.create_table(
        "point_rewards",
        sa.Column("reward_id", sa.Integer(), nullable=False),
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
        sa.Column("reward_name", sa.String(length=100), nullable=False),
        sa.Column("reward_description", sa.Text(), nullable=False),
        sa.Column("reward_type", sa.String(length=30), nullable=False),
        sa.Column("reward_cost", sa.Integer(), nullable=False),
        sa.Column("reward_data", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_limited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_purchases", sa.Integer(), nullable=True),
        sa.Column(
            "current_purchases", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("required_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expiry_date", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("reward_id"),
    )

    # Create point_redemptions table
    op.create_table(
        "point_redemptions",
        sa.Column("redemption_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("reward_id", sa.Integer(), nullable=False),
        sa.Column("points_spent", sa.Integer(), nullable=False),
        sa.Column("reward_data", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="completed"
        ),
        sa.Column("redeemed_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reward_id"], ["point_rewards.reward_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("redemption_id"),
    )

    # Create point_streaks table
    op.create_table(
        "point_streaks",
        sa.Column("streak_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("streak_type", sa.String(length=20), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity", sa.BigInteger(), nullable=False),
        sa.Column("bonus_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("streak_id"),
        sa.UniqueConstraint("user_id", "group_id", "streak_type"),
    )

    # Create point_leaderboards table
    op.create_table(
        "point_leaderboards",
        sa.Column("leaderboard_id", sa.Integer(), nullable=False),
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
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("leaderboard_type", sa.String(length=20), nullable=False),
        sa.Column("top_users", sa.Text(), nullable=False),
        sa.Column("snapshot_time", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("leaderboard_id"),
    )


def _create_managed_channels_table() -> None:
    """Create managed channels table"""

    op.create_table(
        "managed_channels",
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
        sa.Column("channel_name", sa.String(length=255), nullable=False),
        sa.Column(
            "channel_type", sa.String(length=20), nullable=False, server_default="purge"
        ),
        sa.Column("auto_purge", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "owner_can_post", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["added_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("channel_id"),
    )


def _create_member_profiles_table() -> None:
    """Create member profiles table"""

    op.create_table(
        "member_profiles",
        sa.Column("profile_id", sa.Integer(), nullable=False),
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
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("total_messages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stickers_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photos_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("videos_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("voice_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commands_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replies_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "mentions_received", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("peak_hour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hourly_activity", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
        sa.UniqueConstraint("user_id", "group_id"),
    )


def _create_indexes_and_constraints() -> None:
    """Create all necessary indexes and constraints"""

    # Feature management indexes
    op.create_index("ix_feature_toggles_group_id", "feature_toggles", ["group_id"])
    op.create_index(
        "ix_feature_toggles_feature_name", "feature_toggles", ["feature_name"]
    )
    op.create_index("ix_feature_usage_group_id", "feature_usage", ["group_id"])
    op.create_index("ix_feature_usage_user_id", "feature_usage", ["user_id"])
    op.create_index("ix_feature_logs_group_id", "feature_logs", ["group_id"])

    # Flirting system indexes
    op.create_index("ix_flirting_attempts_user_id", "flirting_attempts", ["user_id"])
    op.create_index("ix_flirting_attempts_group_id", "flirting_attempts", ["group_id"])
    op.create_index("ix_flirting_stats_user_id", "flirting_stats", ["user_id"])
    op.create_index(
        "ix_flirting_relationships_user_id", "flirting_relationships", ["user_id"]
    )

    # Bot friendship indexes
    op.create_index("ix_bot_friendships_group_id", "bot_friendships", ["group_id"])
    op.create_index("ix_bot_interactions_group_id", "bot_interactions", ["group_id"])
    op.create_index("ix_bot_memories_group_id", "bot_memories", ["group_id"])

    # Point system indexes
    op.create_index("ix_user_points_user_id", "user_points", ["user_id"])
    op.create_index("ix_user_points_group_id", "user_points", ["group_id"])
    op.create_index("ix_user_points_current_points", "user_points", ["current_points"])
    op.create_index("ix_point_transactions_user_id", "point_transactions", ["user_id"])
    op.create_index("ix_apploids_rarity", "apploids", ["rarity"])
    op.create_index("ix_user_apploids_user_id", "user_apploids", ["user_id"])

    # Member profiles indexes
    op.create_index("ix_member_profiles_user_id", "member_profiles", ["user_id"])
    op.create_index("ix_member_profiles_group_id", "member_profiles", ["group_id"])
    op.create_index(
        "ix_member_profiles_total_messages", "member_profiles", ["total_messages"]
    )

    # Add check constraints for data integrity
    op.create_check_constraint(
        "ck_user_points_non_negative",
        "user_points",
        sa.text("current_points >= 0 AND total_earned >= 0 AND total_spent >= 0"),
    )
    op.create_check_constraint(
        "ck_user_points_level_positive", "user_points", sa.text("level > 0")
    )
    op.create_check_constraint(
        "ck_flirting_attempts_points_non_negative",
        "flirting_attempts",
        sa.text("points_earned >= 0"),
    )
    op.create_check_constraint(
        "ck_bot_friendships_score_valid",
        "bot_friendships",
        sa.text("friendship_score >= 0 AND friendship_score <= 100"),
    )
    op.create_check_constraint(
        "ck_point_transactions_amount_valid",
        "point_transactions",
        sa.text("amount != 0"),
    )


def downgrade() -> None:
    """Remove all feature tables"""

    # Drop tables in reverse order of creation
    tables_to_drop = [
        "member_profiles",
        "managed_channels",
        "point_leaderboards",
        "point_streaks",
        "point_redemptions",
        "point_rewards",
        "user_apploids",
        "apploids",
        "point_transactions",
        "user_points",
        "bot_emotions",
        "bot_conversations",
        "bot_gifts",
        "bot_memories",
        "bot_interactions",
        "bot_friendships",
        "flirting_preferences",
        "flirting_gifts",
        "flirting_relationships",
        "flirting_achievements",
        "flirting_stats",
        "flirting_attempts",
        "feature_logs",
        "feature_usage",
        "feature_permissions",
        "feature_toggles",
    ]

    for table in tables_to_drop:
        try:
            op.drop_table(table)
        except Exception:
            pass  # Table might not exist

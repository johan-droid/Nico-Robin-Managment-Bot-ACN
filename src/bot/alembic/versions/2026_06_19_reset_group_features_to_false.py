"""Reset all auto-response group features to False for existing groups.

This ensures existing groups (created before model defaults were changed)
start quiet — admins must opt-in via /enable or /settings.

Revision ID: 2026_06_19_reset_group_features_to_false
Revises: 2026_05_27_merge_heads_add_welcome_dm
Create Date: 2026-06-19 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_06_19_reset_group_features_to_false"
down_revision: str | None = "2026_05_27_merge_heads_add_welcome_dm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE groups SET
            welcome_enabled = FALSE,
            farewell_enabled = FALSE,
            welcome_dm_enabled = FALSE,
            captcha_enabled = FALSE,
            antispam_enabled = FALSE,
            antiraid_enabled = FALSE,
            ai_mod_enabled = FALSE,
            nightmode_enabled = FALSE,
            swear_words_enabled = FALSE
        """
    )


def downgrade() -> None:
    pass

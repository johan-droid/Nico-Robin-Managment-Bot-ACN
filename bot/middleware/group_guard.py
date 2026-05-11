"""Group guard middleware - restricts bot to ALLOWED_GROUP_IDS only."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from config import settings

logger = structlog.get_logger(__name__)


async def group_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global middleware that blocks updates from non-allowed groups.

    If ALLOWED_GROUP_IDS is empty, all groups are allowed (open mode).
    If ALLOWED_GROUP_IDS is set, ONLY those groups can interact with the bot.
    DM messages from captain/sudo users always pass through.
    """
    chat = update.effective_chat
    user = update.effective_user

    # No chat context (e.g. inline queries) - let through
    if chat is None:
        return

    allowed_ids = settings.allowed_group_ids

    # Open mode: if no groups are configured, allow all
    if not allowed_ids:
        return

    # Private chats: allow for captain, commanders, and sudo users
    if chat.type == "private":
        if user and (
            user.id == settings.captain_id
            or user.id in settings.commander_ids
            or user.id in settings.sudo_users
        ):
            return
        # Block DMs from non-authorized users when restriction is active
        if update.effective_message:
            await update.effective_message.reply_text(
                "🚫 This bot is restricted to Anime Crew Network groups only."
            )
        raise _StopProcessing()

    # Group/supergroup/channel: check against allowed list
    if chat.id not in allowed_ids:
        logger.warning(
            "unauthorized_group_access",
            group_id=chat.id,
            group_title=chat.title,
            user_id=user.id if user else None,
        )
        # Silently ignore - don't spam unauthorized groups
        raise _StopProcessing()


class _StopProcessing(Exception):
    """Sentinel to halt handler processing via error handler."""

    pass


async def group_guard_error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Suppress _StopProcessing exceptions raised by the group guard."""
    if isinstance(context.error, _StopProcessing):
        return  # Silently swallow - this is expected behavior
    # Re-raise any other errors so they propagate normally
    raise context.error

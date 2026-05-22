"""Channel guard plugin - auto-purge channel posts & owner custom posting."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes, MessageHandler
from telegram.ext import filters as tg_filters

from src.bot.config import settings
from src.bot.database import async_session_factory
from src.bot.models.managed_channel import ManagedChannel
from src.bot.services.acn_service import captain_commander_only

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Auto-purge handler
# ---------------------------------------------------------------------------


async def auto_purge_channel_post(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Auto-delete new posts in purge-listed channels.

    Posts made by the Captain (owner) are preserved.
    Channels can be configured via env var PURGE_CHANNEL_IDS or dynamically
    with /addpurgechannel.
    """
    message = update.channel_post
    if message is None or message.chat is None:
        return

    channel_id = message.chat.id

    # Check env-var list first (fast path)
    is_purge_target = channel_id in settings.purge_channel_ids

    # Check database list if not in env
    if not is_purge_target:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ManagedChannel).where(
                    ManagedChannel.channel_id == channel_id,
                    ManagedChannel.auto_purge,
                )
            )
            is_purge_target = result.scalar_one_or_none() is not None

    if not is_purge_target:
        return

    # Check if message was posted by the owner (Captain) — allow through
    # Channel posts from admins have sender_chat set to the channel itself
    # and message.from_user is usually None. We check via bot API if possible.
    if message.from_user and message.from_user.id == settings.captain_id:
        logger.info(
            "captain_channel_post_allowed",
            channel_id=channel_id,
            message_id=message.message_id,
        )
        return

    # Auto-purge the post
    try:
        await message.delete()
        logger.info(
            "channel_post_purged",
            channel_id=channel_id,
            message_id=message.message_id,
        )
    except TelegramError as exc:
        logger.warning(
            "channel_purge_failed",
            channel_id=channel_id,
            message_id=message.message_id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Channel management commands
# ---------------------------------------------------------------------------


@captain_commander_only
async def add_purge_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a channel to the purge list (Captain/Commander only)."""
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if not args:
        await msg.reply_text(
            "🌸 Usage: `/addpurgechannel <channel_id> [name]`\n"
            "Example: `/addpurgechannel -1001234567890 My Channel`"
        )
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        await msg.reply_text("🌸 Invalid channel ID. Please provide a numeric ID.")
        return

    channel_name = " ".join(args[1:]) if len(args) > 1 else f"Channel {channel_id}"

    async with async_session_factory() as session:
        async with session.begin():
            # Check if already exists
            result = await session.execute(
                select(ManagedChannel).where(ManagedChannel.channel_id == channel_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.auto_purge = True
                existing.channel_name = channel_name
            else:
                channel = ManagedChannel(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    channel_type="purge",
                    auto_purge=True,
                    owner_can_post=True,
                    added_by=(
                        update.effective_user.id if update.effective_user else None
                    ),
                )
                session.add(channel)

    await msg.reply_text(
        f"🌸 **Purge Channel Added!**\n\n"
        f"📺 {channel_name}\n"
        f"🆔 `{channel_id}`\n"
        f"🗑️ New posts will be auto-deleted.\n"
        f"⚓ Captain's posts are preserved."
    )


@captain_commander_only
async def remove_purge_channel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove a channel from the purge list (Captain/Commander only)."""
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if not args:
        await msg.reply_text("🌸 Usage: `/removepurgechannel <channel_id>`")
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        await msg.reply_text("🌸 Invalid channel ID.")
        return

    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(ManagedChannel).where(ManagedChannel.channel_id == channel_id)
            )
            channel = result.scalar_one_or_none()

            if channel:
                channel.auto_purge = False
                await msg.reply_text(
                    f"🌸 **Purge Disabled!**\n\n"
                    f"📺 {channel.channel_name} will no longer be auto-purged."
                )
            else:
                await msg.reply_text("🌸 Channel not found in managed list.")


@captain_commander_only
async def list_purge_channels(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """List all channels being auto-purged."""
    msg = update.effective_message
    if msg is None:
        return

    # Gather from env
    env_channels = list(settings.purge_channel_ids)

    # Gather from DB
    async with async_session_factory() as session:
        result = await session.execute(
            select(ManagedChannel).where(ManagedChannel.auto_purge)
        )
        db_channels = result.scalars().all()

    if not env_channels and not db_channels:
        await msg.reply_text("🌸 No purge channels configured.")
        return

    response = "🌸 **Auto-Purge Channels**\n\n"

    if env_channels:
        response += "📋 **From Environment:**\n"
        for cid in env_channels:
            response += f"  🗑️ `{cid}`\n"
        response += "\n"

    if db_channels:
        response += "📋 **From Database:**\n"
        for ch in db_channels:
            response += f"  🗑️ {ch.channel_name} (`{ch.channel_id}`)\n"

    await msg.reply_text(response, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Owner custom post to channel
# ---------------------------------------------------------------------------


@captain_commander_only
async def channel_post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post a custom message to a managed channel (Captain/Commander only).

    Usage:
        /channelpost <channel_id> <message>
        Reply to a message with /channelpost <channel_id> to forward it.
    """
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if not args:
        await msg.reply_text(
            "🌸 Usage: `/channelpost <channel_id> <message>`\n"
            "Or reply to a message with `/channelpost <channel_id>`"
        )
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        await msg.reply_text("🌸 Invalid channel ID.")
        return

    # Build content to post
    text_content = " ".join(args[1:]).strip() if len(args) > 1 else ""

    # If replying to a message, forward it
    if msg.reply_to_message and not text_content:
        try:
            await context.bot.forward_message(
                chat_id=channel_id,
                from_chat_id=msg.chat.id,
                message_id=msg.reply_to_message.message_id,
            )
            await msg.reply_text(f"🌸 Message forwarded to channel `{channel_id}`.")
            return
        except TelegramError as exc:
            await msg.reply_text(f"🌸 Failed to forward: {exc}")
            return

    if not text_content:
        await msg.reply_text("🌸 Please provide a message to post or reply to one.")
        return

    # Send custom text post
    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=text_content,
            parse_mode="Markdown",
        )
        await msg.reply_text(
            f"🌸 **Posted to channel!**\n"
            f"📺 Channel: `{channel_id}`\n"
            f"📝 Content: {text_content[:100]}{'...' if len(text_content) > 100 else ''}"
        )
    except TelegramError as exc:
        await msg.reply_text(f"🌸 Failed to post: {exc}")


@captain_commander_only
async def channel_photo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward a photo reply to a managed channel (Captain/Commander only).

    Usage: Reply to a photo with /channelphoto <channel_id> [caption]
    """
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if not args:
        await msg.reply_text(
            "🌸 Usage: Reply to a photo with `/channelphoto <channel_id> [caption]`"
        )
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        await msg.reply_text("🌸 Invalid channel ID.")
        return

    reply = msg.reply_to_message
    if not reply or not reply.photo:
        await msg.reply_text("🌸 Please reply to a photo to send it to the channel.")
        return

    caption = " ".join(args[1:]).strip() or reply.caption or ""

    try:
        await context.bot.send_photo(
            chat_id=channel_id,
            photo=reply.photo[-1].file_id,
            caption=caption,
            parse_mode="Markdown",
        )
        await msg.reply_text(f"🌸 Photo sent to channel `{channel_id}`.")
    except TelegramError as exc:
        await msg.reply_text(f"🌸 Failed to send photo: {exc}")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(app) -> None:
    """Register channel guard handlers and commands."""
    # Auto-purge handler — runs at group=0 (high priority)
    app.add_handler(
        MessageHandler(
            tg_filters.UpdateType.CHANNEL_POST,
            auto_purge_channel_post,
        ),
        group=0,
    )

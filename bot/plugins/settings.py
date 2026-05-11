from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database import async_session_factory
from services.group_service import GroupService
from utils.decorators import admin_only, group_only


@group_only
@admin_only
async def setlocale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    locale = (context.args or [""])[0].lower()
    if msg is None or chat is None or locale not in {"en", "hi", "ja", "es", "ru"}:
        if msg:
            await msg.reply_text("🌸 Choose locale: en, hi, ja, es, or ru.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, locale=locale)
    await msg.reply_text(f"🌸 Locale set to {locale}.")


@group_only
@admin_only
async def setwarnlimit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    if not context.args:
        await msg.reply_text(
            "🌸 Please specify a warning limit.\n"
            "Usage: `/setwarnlimit <number>` (1-10)\n"
            "Example: `/setwarnlimit 3`"
        )
        return

    try:
        limit = int(context.args[0])
        if limit < 1 or limit > 10:
            await msg.reply_text(
                "🌸 Warning limit must be between 1 and 10.\n"
                "Recommended: 3-5 for most groups."
            )
            return
    except ValueError:
        await msg.reply_text(
            "🌸 Please provide a valid number.\nUsage: `/setwarnlimit <number>` (1-10)"
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, max_warns=limit)

    await msg.reply_text(
        f"🌸 Warning limit set to {limit}.\n"
        f"Users will be automatically {'banned' if limit <= 3 else 'kicked' if limit <= 5 else 'muted'} "
        f"after {limit} warnings."
    )


@group_only
@admin_only
async def setwarnaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    if not context.args:
        await msg.reply_text(
            "🌸 Please specify a warning action.\n"
            "Usage: `/setwarnaction <action>\n"
            "Available actions: ban, kick, mute\n\n"
            "• ban: Permanently removes user from group\n"
            "• kick: Removes user (can rejoin)\n"
            "• mute: Silences user temporarily"
        )
        return

    action = context.args[0].lower()
    valid_actions = {"ban", "kick", "mute"}

    if action not in valid_actions:
        await msg.reply_text(
            f"🌸 Invalid action '{action}'.\n"
            f"Available actions: {', '.join(valid_actions)}\n\n"
            f"Usage: `/setwarnaction <action>`"
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, warn_action=action)

    action_descriptions = {
        "ban": "permanently banned",
        "kick": "kicked (can rejoin)",
        "mute": "muted temporarily",
    }

    await msg.reply_text(
        f"🌸 Warning action set to {action}.\n"
        f"Users will now be {action_descriptions[action]} when they reach the warning limit."
    )


@group_only
@admin_only
async def setlogchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set the log channel for this group.

    The log channel receives notifications about member joins, leaves,
    and moderation actions.

    Usage: /setlogchannel <channel_id>
    """
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if not args:
        await msg.reply_text(
            "🌸 Usage: `/setlogchannel <channel_id>`\n"
            "Example: `/setlogchannel -1001234567890`\n\n"
            "The bot must be an admin in the log channel."
        )
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        await msg.reply_text("🌸 Invalid channel ID. Please provide a numeric ID.")
        return

    # Verify bot can send to this channel
    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=f"🌸 Log channel configured for **{chat.title}**.\n"
            f"Member joins, leaves, and moderation actions will appear here.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        await msg.reply_text(
            f"🌸 Cannot send to channel `{channel_id}`. "
            f"Make sure the bot is an admin there.\n"
            f"Error: {exc}"
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(
                session, chat.id, log_channel_id=channel_id
            )

    await msg.reply_text(
        f"🌸 **Log Channel Set!**\n\n"
        f"📋 Channel: `{channel_id}`\n"
        f"👋 New member joins will be logged.\n"
        f"🚪 Member departures will be logged.\n"
        f"🛡️ Moderation actions will be logged."
    )


@group_only
@admin_only
async def removelogchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the log channel for this group."""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, log_channel_id=None)

    await msg.reply_text(
        "🌸 Log channel removed. Member tracking will use the global log channel (if set)."
    )


def register(app) -> None:
    app.add_handler(CommandHandler("setlocale", setlocale))
    app.add_handler(CommandHandler("setwarnlimit", setwarnlimit))
    app.add_handler(CommandHandler("setwarnaction", setwarnaction))
    app.add_handler(CommandHandler("setlogchannel", setlogchannel))
    app.add_handler(CommandHandler("removelogchannel", removelogchannel))

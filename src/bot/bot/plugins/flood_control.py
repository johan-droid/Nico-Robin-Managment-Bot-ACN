from __future__ import annotations

from datetime import timedelta

import structlog
from telegram import ChatPermissions, Update
from telegram.error import TelegramError
from telegram.ext import (
    ContextTypes,
    MessageHandler,
)
from telegram.ext import (
    filters as tg_filters,
)

from src.bot.bot.middleware.flood_control import check_flood
from src.bot.database import async_session_factory
from src.bot.services.audit_service import AuditService
from src.bot.services.group_service import GroupService
from src.bot.services.user_service import UserService
from src.bot.utils.decorators import admin_only, group_only
from src.bot.utils.i18n import gettext
from src.bot.utils.permissions import is_telegram_admin
from src.bot.utils.time import parse_duration, until_datetime

logger = structlog.get_logger(__name__)


@group_only
@admin_only
async def setflood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    try:
        limit = int((context.args or [""])[0])
    except ValueError:
        await msg.reply_text("🌸 Give me a number of messages per five seconds.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(
                session,
                chat.id,
                flood_limit=max(limit, 0),
                antispam_enabled=limit > 0,
            )
    if limit <= 0:
        await msg.reply_text(gettext("flood.disabled"))
    else:
        await msg.reply_text(gettext("flood.configured", limit=limit))


@group_only
@admin_only
async def setfloodmode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    mode = " ".join(context.args or []).strip().lower()
    if not mode or mode.split()[0] not in {"ban", "kick", "mute", "tban", "tmute"}:
        await msg.reply_text("🌸 Choose: ban, kick, mute, tban 1h, or tmute 10m.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, flood_action=mode)
    await msg.reply_text(gettext("flood.mode", mode=mode))


@group_only
async def flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    async with async_session_factory() as session:
        group = await GroupService.get_group(session, chat.id)
    if group is None:
        await msg.reply_text(
            "🌸 Flood control is using the default archive: 5 messages / 5 seconds."
        )
    else:
        await msg.reply_text(
            f"🌸 Flood limit: {group.flood_limit}/5s. Action: {group.flood_action}."
        )


async def _apply_flood_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    default_mute_seconds: int,
) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    parts = action.split()
    mode = parts[0]
    duration = parse_duration(parts[1]) if len(parts) > 1 else None
    if mode == "ban":
        await context.bot.ban_chat_member(chat.id, user.id)
    elif mode == "kick":
        await context.bot.ban_chat_member(chat.id, user.id)
        await context.bot.unban_chat_member(chat.id, user.id, only_if_banned=True)
    elif mode == "mute":
        await context.bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_datetime(timedelta(seconds=default_mute_seconds)),
        )
    elif mode == "tban":
        await context.bot.ban_chat_member(
            chat.id,
            user.id,
            until_date=until_datetime(duration or timedelta(hours=1)),
        )
    elif mode == "tmute":
        await context.bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_datetime(duration or timedelta(minutes=10)),
        )


@group_only
async def handle_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None or user.is_bot:
        return
    try:
        if await is_telegram_admin(context, chat.id, user.id):
            return
    except TelegramError:
        return
    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)
            await UserService.ensure_user(session, user)
        limit = group.flood_limit
        enabled = group.antispam_enabled
        action = group.flood_action
        mute_time = group.mute_time
    if not enabled or not await check_flood(chat.id, user.id, limit):
        return
    try:
        await _apply_flood_action(update, context, action, mute_time)
    except TelegramError as exc:
        logger.warning(
            "flood_action_failed", chat_id=chat.id, user_id=user.id, error=str(exc)
        )
    async with async_session_factory() as session:
        async with session.begin():
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action=f"flood_{action.split()[0]}",
                actor_id=None,
                target_id=user.id,
                reason="Flood threshold exceeded",
                extra={"limit": limit},
            )
    await msg.reply_text(gettext("flood.detected"))


def register(app) -> None:
    app.add_handler(
        MessageHandler(tg_filters.ALL & ~tg_filters.COMMAND, handle_flood),
        group=10,
    )

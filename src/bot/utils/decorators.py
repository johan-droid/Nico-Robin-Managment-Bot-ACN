from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, cast

from sqlalchemy import select
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.bot.database import async_session_factory
from src.bot.models.group import Group
from src.bot.services.security_logger import SecurityLogger
from src.bot.utils.i18n import gettext
from src.bot.utils.permissions import (
    bot_has_admin_rights,
    is_anonymous_admin_message,
    is_group_chat,
    is_sudo,
    is_telegram_admin,
    is_telegram_owner,
)
from src.bot.utils.sanitizer import sanitize_input  # noqa: F401 — re-exported

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]


async def _reply(update: Update, text: str) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text)


def bot_rights_required(*rights: str) -> Handler:
    def decorator(func: Handler) -> Handler:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat = update.effective_chat
            if chat is None:
                await _reply(update, gettext("admin.no_authority"))
                return
            try:
                has_rights = await bot_has_admin_rights(context, chat.id, *rights)
            except TelegramError:
                has_rights = False
            if not has_rights:
                await SecurityLogger.log_event(
                    event_type="bot_missing_rights",
                    user_id=update.effective_user.id if update.effective_user else None,
                    chat_id=chat.id,
                    severity="MEDIUM",
                    details={"rights": list(rights)},
                )
                await _reply(
                    update, "🌸 I cannot do that without the proper authority."
                )
                return
            await func(update, context)

        return cast(Handler, wrapper)

    return decorator


def group_only(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not is_group_chat(update.effective_chat):
            await _reply(update, gettext("group.only"))
            return
        await func(update, context)

    return cast(Handler, wrapper)


def sudo_only(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not is_sudo(user.id if user else None):
            await _reply(update, gettext("admin.sudo_only"))
            return
        await func(update, context)

    return cast(Handler, wrapper)


def admin_only(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message
        if user is None or chat is None:
            await _reply(update, gettext("admin.no_authority"))
            return
        if is_anonymous_admin_message(message):
            await SecurityLogger.log_event(
                event_type="anonymous_admin_rejected",
                user_id=None,
                chat_id=chat.id,
                severity="MEDIUM",
                details={"command": message.text if message and message.text else ""},
            )
            await _reply(update, "🌸 Sensitive commands cannot be issued anonymously.")
            return
        try:
            if not await is_telegram_admin(context, chat.id, user.id):
                await SecurityLogger.log_event(
                    event_type="permission_denied",
                    user_id=user.id,
                    chat_id=chat.id,
                    severity="MEDIUM",
                    details={"scope": "admin_only"},
                )
                await _reply(update, gettext("admin.no_authority"))
                return
        except TelegramError:
            await SecurityLogger.log_event(
                event_type="permission_check_failed",
                user_id=user.id,
                chat_id=chat.id,
                severity="HIGH",
                details={"scope": "admin_only"},
            )
            await _reply(update, gettext("admin.no_authority"))
            return
        await func(update, context)

    return cast(Handler, wrapper)


def owner_only(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            await _reply(update, gettext("admin.owner_only"))
            return
        if is_anonymous_admin_message(update.effective_message):
            await _reply(update, "🌸 Owner-level actions cannot be issued anonymously.")
            return
        if is_sudo(user.id):
            await func(update, context)
            return
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Group).where(Group.group_id == chat.id)
                )
                group = result.scalar_one_or_none()
        except Exception:
            await _reply(update, gettext("admin.owner_only"))
            return
        try:
            is_owner = await is_telegram_owner(context, chat.id, user.id)
        except TelegramError:
            is_owner = False
        if not is_owner and (group is None or group.owner_id != user.id):
            await _reply(update, gettext("admin.owner_only"))
            return
        await func(update, context)

    return cast(Handler, wrapper)

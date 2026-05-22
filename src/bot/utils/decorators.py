from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
import traceback
from typing import Any, cast

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.bot.database import async_session_factory
from src.bot.models.group import Group
from src.bot.services.acn_service import ACNService
from src.bot.services.feature_service import FeatureService
from src.bot.utils.i18n import gettext
from src.bot.utils.permissions import (
    is_group_chat,
    is_sudo,
    is_telegram_owner,
)
from src.bot.utils.sanitizer import sanitize_input  # noqa: F401 — re-exported

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]

logger = structlog.get_logger(__name__)


class BotPermissionError(RuntimeError):
    """Raised when the bot lacks the Telegram rights needed for moderation."""


def _extract_command_name(update: Update | None) -> str | None:
    if update is None or update.effective_message is None:
        return None

    text = update.effective_message.text or update.effective_message.caption or ""
    if not text.startswith("/"):
        return None
    return text.split()[0].split("@", 1)[0][1:]


def log_command(func: Handler) -> Handler:
    """Log command failures with traceback, then re-raise for PTB error handlers."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await func(update, context)
        except Exception as exc:
            command_name = _extract_command_name(update) or func.__name__
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            logger.error(
                "command_failed",
                command=command_name,
                callback=func.__name__,
                error=str(exc),
                traceback=tb,
                chat_id=update.effective_chat.id if update.effective_chat else None,
                user_id=update.effective_user.id if update.effective_user else None,
            )
            raise

    return cast(Handler, wrapper)


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return False

    bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
    if bot_member.status not in {"administrator", "creator"}:
        raise BotPermissionError(
            "I need to be an admin in this chat before I can moderate it."
        )
    if bot_member.status == "administrator" and not getattr(
        bot_member, "can_restrict_members", False
    ):
        raise BotPermissionError(
            "I need the can_restrict_members permission to moderate members here."
        )

    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in {"administrator", "creator"}


async def _reply(update: Update, text: str) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text)


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


def require_admin(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if not await is_admin(update, context):
                await _reply(update, gettext("admin.no_authority"))
                return
        except BotPermissionError as exc:
            await _reply(update, f"🌸 {exc}")
            return
        except TelegramError:
            await _reply(update, gettext("admin.no_authority"))
            return
        await func(update, context)

    return cast(Handler, wrapper)


def admin_only(func: Handler) -> Handler:
    return require_admin(func)


def require_captain_commander(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            await _reply(update, gettext("admin.captain_commander_only"))
            return

        if not (await ACNService.is_captain(user.id) or await ACNService.is_commander(user.id)):
            await _reply(update, gettext("admin.captain_commander_only"))
            return

        await func(update, context)

    return cast(Handler, wrapper)


def feature_enabled(feature_name: str) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat = update.effective_chat
            if chat is None:
                return

            if not await FeatureService.is_feature_enabled(chat.id, feature_name):
                await _reply(update, gettext("feature.disabled"))
                return

            await func(update, context)

        return cast(Handler, wrapper)

    return decorator


def owner_only(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            await _reply(update, gettext("admin.owner_only"))
            return
        if is_sudo(user.id):
            await func(update, context)
            return
        async with async_session_factory() as session:
            result = await session.execute(
                select(Group).where(Group.group_id == chat.id)
            )
            group = result.scalar_one_or_none()
        try:
            is_owner = await is_telegram_owner(context, chat.id, user.id)
        except TelegramError:
            is_owner = False
        if not is_owner and (group is None or group.owner_id != user.id):
            await _reply(update, gettext("admin.owner_only"))
            return
        await func(update, context)

    return cast(Handler, wrapper)

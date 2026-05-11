from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Coroutine, cast

from sqlalchemy import select
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from database import async_session_factory
from models.group import Group
from utils.i18n import gettext
from utils.permissions import (
    is_group_chat,
    is_sudo,
    is_telegram_admin,
    is_telegram_owner,
)
from utils.sanitizer import sanitize_input  # noqa: F401 — re-exported

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]


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


def admin_only(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            await _reply(update, gettext("admin.no_authority"))
            return
        try:
            if not await is_telegram_admin(context, chat.id, user.id):
                await _reply(update, gettext("admin.no_authority"))
                return
        except TelegramError:
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

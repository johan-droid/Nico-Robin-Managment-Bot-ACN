from __future__ import annotations

import functools
import logging
import traceback
from collections.abc import Callable, Coroutine
from typing import Any, cast

from telegram import Update
from telegram.ext import ContextTypes

from .cache import cache
from .database import database

logger = logging.getLogger(__name__)
Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]


def _raw_command(update: Update | None) -> str | None:
    if update is None or update.effective_message is None:
        return None
    text = update.effective_message.text or update.effective_message.caption or ""
    if not text.startswith("/"):
        return None
    return text.split()[0].split("@", 1)[0][1:]


def _app_data(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    application = getattr(context, "application", None)
    if application is None:
        return {}
    return application.bot_data


def _reply(update: Update | None, text: str) -> None:
    if update is not None and update.effective_message is not None:
        return update.effective_message.reply_text(text)
    return None


async def _is_captain(user_id: int | None) -> bool:
    if user_id is None:
        return False
    row = await database.fetchone("SELECT 1 FROM captains WHERE user_id = ?", (user_id,))
    return row is not None


async def _is_commander(user_id: int | None) -> bool:
    if user_id is None:
        return False
    row = await database.fetchone("SELECT 1 FROM commanders WHERE user_id = ?", (user_id,))
    return row is not None


async def _is_admin_cached(chat_id: int, user_id: int) -> bool:
    admin_ids = cache.get(f"admin_cache:{chat_id}")
    if isinstance(admin_ids, list) and user_id in admin_ids:
        return True
    if await _is_captain(user_id) or await _is_commander(user_id):
        return True
    return False


def log_command(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        command_name = _raw_command(update) or func.__name__
        try:
            await func(update, context)
            await database.execute(
                """
                INSERT INTO command_logs (command_name, user_id, chat_id, payload, success, error_text)
                VALUES (?, ?, ?, ?, 1, NULL)
                """,
                (
                    command_name,
                    update.effective_user.id if update.effective_user else None,
                    update.effective_chat.id if update.effective_chat else None,
                    update.effective_message.text if update.effective_message else None,
                ),
            )
        except Exception as exc:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            logger.exception(
                "command_failed",
                extra={"command": command_name, "traceback": tb},
            )
            await database.execute(
                """
                INSERT INTO command_logs (command_name, user_id, chat_id, payload, success, error_text)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (
                    command_name,
                    update.effective_user.id if update.effective_user else None,
                    update.effective_chat.id if update.effective_chat else None,
                    update.effective_message.text if update.effective_message else None,
                    str(exc)[:1000],
                ),
            )
            raise

    return cast(Handler, wrapper)


def require_captain(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None or not await _is_captain(user.id):
            await _reply(update, "🌸 Only the Captain can use this command.")
            return
        await func(update, context)

    return cast(Handler, wrapper)


def require_commander_or_captain(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None or not (await _is_captain(user.id) or await _is_commander(user.id)):
            await _reply(update, "🌸 Only the Captain or Commanders can use this command.")
            return
        await func(update, context)

    return cast(Handler, wrapper)


def require_admin(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None or not await _is_admin_cached(chat.id, user.id):
            await _reply(update, "🌸 Admin rights are required.")
            return
        await func(update, context)

    return cast(Handler, wrapper)


def feature_toggle(feature_name: str) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat = update.effective_chat
            if chat is None:
                return
            cache_key = f"feature:{chat.id}:{feature_name}"
            enabled = cache.get(cache_key)
            if enabled is None:
                row = await database.fetchone(
                    "SELECT enabled FROM group_features WHERE group_id = ? AND feature_name = ?",
                    (chat.id, feature_name),
                )
                enabled = True if row is None else bool(row[0])
                cache.set(cache_key, enabled, ttl=60)
            if not enabled:
                await _reply(update, "This feature is disabled.")
                return
            await func(update, context)

        return cast(Handler, wrapper)

    return decorator


def get_runtime(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    return _app_data(context)


def invalidate_feature_cache(group_id: int, feature_name: str) -> None:
    cache.delete(f"feature:{group_id}:{feature_name}")

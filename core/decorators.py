from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from core.admin_cache import AdminCache
from core.cache import Cache
from core.database import DatabaseManager

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
logger = logging.getLogger(__name__)


def _db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    return context.application.bot_data["db"]


def _cache(context: ContextTypes.DEFAULT_TYPE) -> Cache:
    return context.application.bot_data["cache"]


def _admin_cache(context: ContextTypes.DEFAULT_TYPE) -> AdminCache:
    return context.application.bot_data["admin_cache"]


async def _get_role_from_cache_or_db(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> str | None:
    cache = _cache(context)
    key = f"role:{user_id}"
    cached = cache.get(key)
    if cached is not None:
        return str(cached)
    role = await _db(context).get_user_role(user_id)
    if role is not None:
        cache.set(key, role, ttl=300)
    return role


async def _is_captain(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    role = await _get_role_from_cache_or_db(context, user_id)
    return role == "Captain"


async def _is_commander_or_captain(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    role = await _get_role_from_cache_or_db(context, user_id)
    return role in {"Captain", "Commander"}


async def _is_whitelisted_member(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    role = await _get_role_from_cache_or_db(context, user_id)
    return role in {"Captain", "Commander", "Member"}


def require_captain(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            return
        if not await _is_captain(context, user.id):
            if update.effective_message:
                await update.effective_message.reply_text("Captain access required.")
            return
        await func(update, context)

    return wrapper


def require_commander_or_captain(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            return
        if not await _is_commander_or_captain(context, user.id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Commander or Captain access required."
                )
            return
        await func(update, context)

    return wrapper


def require_admin(func: Handler) -> Handler:
    """Rose-style admin check via admin cache, with Captain/Commander bypass."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            return

        if await _is_commander_or_captain(context, user.id):
            await func(update, context)
            return

        await _admin_cache(context).remember_group(chat.id)
        if not await _admin_cache(context).is_admin(context.bot, chat.id, user.id):
            if update.effective_message:
                await update.effective_message.reply_text("Admin access required.")
            return
        await func(update, context)

    return wrapper


def require_acn_member(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            return
        if not await _is_whitelisted_member(context, user.id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "This command is for ACN members. Ask a captain to add you."
                )
            return
        await func(update, context)

    return wrapper


def feature_toggle(feature_name: str) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat = update.effective_chat
            if chat is None:
                return
            cache = _cache(context)
            key = f"feature:{chat.id}:{feature_name}"
            enabled = cache.get(key)
            if enabled is None:
                enabled = await _db(context).get_feature_enabled(chat.id, feature_name)
                cache.set(key, bool(enabled), ttl=300)

            if not bool(enabled):
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "This feature is disabled."
                    )
                return
            await func(update, context)

        return wrapper

    return decorator


def log_command(func: Handler) -> Handler:
    """Logs command usage in moderation_log table for auditing."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message
        if user is None or chat is None:
            await func(update, context)
            return

        command = ""
        if msg and msg.text:
            command = msg.text.split()[0].lstrip("/")

        try:
            await func(update, context)
        finally:
            try:
                await _db(context).log_moderation(
                    action_type=f"cmd:{command or func.__name__}",
                    moderator_id=user.id,
                    target_id=None,
                    group_id=chat.id,
                    reason="command usage",
                )
            except Exception:
                logger.exception("command_log_failed", extra={"command": command})

    return wrapper

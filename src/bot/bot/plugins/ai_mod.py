from __future__ import annotations

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    ContextTypes,
    MessageHandler,
)
from telegram.ext import (
    filters as tg_filters,
)

from src.bot.config import settings
from src.bot.database import async_session_factory
from src.bot.services.audit_service import AuditService
from src.bot.services.group_service import GroupService
from src.bot.services.moderation_engine import ModerationResult, get_moderation_engine
from src.bot.services.security_audit_service import SecurityAuditService
from src.bot.services.user_service import UserService
from src.bot.services.warn_service import WarnService
from src.bot.utils.decorators import admin_only, feature_enabled, group_only
from src.bot.utils.i18n import gettext
from src.bot.utils.permissions import is_telegram_admin


def _state_arg(args: list[str]) -> bool | None:
    if not args:
        return None
    raw = args[0].lower()
    if raw in {"on", "yes", "true", "enable", "enabled"}:
        return True
    if raw in {"off", "no", "false", "disable", "disabled"}:
        return False
    return None


@group_only
@admin_only
async def toggleai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    state = _state_arg(context.args or [])
    if state is None:
        await msg.reply_text("🌸 Choose on or off for offline moderation.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, ai_mod_enabled=state)
    await msg.reply_text(f"🌸 Offline moderation is now {'on' if state else 'off'}.")


async def _apply_ai_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    result: ModerationResult,
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return
    reason = f"Offline moderation: {result.category} ({result.score:.2f})"
    if result.action in {"delete", "delete_warn"}:
        try:
            await msg.delete()
        except TelegramError:
            pass
    if result.action in {"warn", "delete_warn"}:
        async with async_session_factory() as session:
            async with session.begin():
                await UserService.ensure_user(session, user)
                await WarnService.issue_warn(
                    session,
                    group_id=chat.id,
                    user_id=user.id,
                    admin_id=None,
                    reason=reason,
                )
    elif result.action == "ban":
        await context.bot.ban_chat_member(chat.id, user.id)
    elif result.action == "notify_admin":
        await msg.reply_text(
            gettext("ai.flagged", category=result.category, score=f"{result.score:.2f}")
        )

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await UserService.ensure_user(session, user)
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action=f"offline_mod_{result.action}",
                actor_id=None,
                target_id=user.id,
                reason=reason,
                extra={"category": result.category, "score": result.score},
            )
            await SecurityAuditService.log_event(
                session=session,
                event_type="offline_moderation",
                severity="MEDIUM",
                user_id=user.id,
                group_id=chat.id,
                reason=reason,
                details={
                    "category": result.category,
                    "score": result.score,
                    "action": result.action,
                },
            )


@group_only
@feature_enabled("ai_moderation")
async def handle_ai_moderation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not settings.ai_moderation_enabled:
        return
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None or user.is_bot or not msg.text:
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
    if not group.ai_mod_enabled:
        return
    result = await get_moderation_engine().moderate(
        msg.text,
        {
            "chat_id": chat.id,
            "chat_title": chat.title,
            "user_id": user.id,
            "username": user.username,
            "group_id": chat.id,
        },
    )
    if result.action == "none" or result.score < settings.ai_score_threshold:
        return
    await _apply_ai_action(update, context, result)


def register(app) -> None:
    app.add_handler(
        MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, handle_ai_moderation),
        group=30,
    )

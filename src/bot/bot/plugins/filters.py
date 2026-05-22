from __future__ import annotations

from telegram import ChatPermissions, Update
from telegram.ext import (
    ContextTypes,
    MessageHandler,
)
from telegram.ext import (
    filters as tg_filters,
)

from src.bot.database import async_session_factory
from src.bot.services.audit_service import AuditService
from src.bot.services.filter_service import FilterService, MatchedFilter
from src.bot.services.group_service import GroupService
from src.bot.services.user_service import UserService
from src.bot.services.warn_service import WarnService
from src.bot.utils.decorators import admin_only, group_only
from src.bot.utils.i18n import gettext
from src.bot.utils.permissions import is_telegram_admin

VALID_ACTIONS = {"reply", "delete", "warn", "ban", "mute"}


def _filter_help() -> str:
    return "🌸 Usage: /filter trigger response | /filter trigger /regex response"


@group_only
@admin_only
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    args = context.args or []
    if not args:
        await msg.reply_text(_filter_help())
        return
    trigger = args[0]
    regex = len(args) > 1 and args[1] == "/regex"
    response_start = 2 if regex else 1
    response = " ".join(args[response_start:]).strip()
    if not response and msg.reply_to_message:
        response = (
            msg.reply_to_message.text_html or msg.reply_to_message.caption_html or ""
        )
    if not response:
        await msg.reply_text(_filter_help())
        return
    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)
            if update.effective_user:
                await UserService.ensure_user(session, update.effective_user)
            await FilterService.add_filter(
                session=session,
                group_id=chat.id,
                trigger=trigger,
                response=response,
                action=group.filter_action,
                regex=regex,
                created_by=update.effective_user.id if update.effective_user else None,
            )
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action="filter_add",
                actor_id=update.effective_user.id if update.effective_user else None,
                reason=trigger,
            )
    await msg.reply_text(gettext("filter.saved", trigger=trigger))


@group_only
@admin_only
async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    args = context.args or []
    if not args:
        await msg.reply_text("🌸 Tell me which filter page to clear.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            removed = await FilterService.remove_filter(session, chat.id, args[0])
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action="filter_remove",
                actor_id=update.effective_user.id if update.effective_user else None,
                reason=args[0],
            )
    if removed:
        await msg.reply_text(gettext("filter.removed"))
    else:
        await msg.reply_text("🌸 I could not find that filter in the archive.")


@group_only
async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    async with async_session_factory() as session:
        items = await FilterService.list_filters(session, chat.id)
    if not items:
        await msg.reply_text(gettext("filter.none"))
        return
    lines = ["🌸 Archived filters:"]
    lines.extend(f"- {item.trigger} -> {item.action}" for item in items)
    await msg.reply_text("\n".join(lines))


@group_only
@admin_only
async def filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    args = context.args or []
    action = args[0].lower() if args else ""
    if action not in VALID_ACTIONS:
        await msg.reply_text("🌸 Choose one action: reply, delete, warn, ban, mute.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, filter_action=action)
    await msg.reply_text(f"🌸 Default filter action set to {action}.")


async def _apply_filter_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    matched: MatchedFilter,
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return
    action = matched.filter.action
    reason = f"Filter matched: {matched.filter.trigger}"
    if matched.filter.response and action == "reply":
        await msg.reply_text(matched.filter.response)
    elif action == "delete":
        await msg.delete()
    elif action == "ban":
        await context.bot.ban_chat_member(chat.id, user.id)
    elif action == "mute":
        await context.bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
    elif action == "warn":
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
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await UserService.ensure_user(session, user)
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action=f"filter_{action}",
                actor_id=None,
                target_id=user.id,
                reason=reason,
            )


@group_only
async def handle_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None or not msg.text:
        return
    if await is_telegram_admin(context, chat.id, user.id):
        return
    async with async_session_factory() as session:
        matches = await FilterService.match_filters(session, chat.id, msg.text)
    if not matches:
        return
    await _apply_filter_action(update, context, matches[0])


def register(app) -> None:
    app.add_handler(
        MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, handle_filters),
        group=20,
    )

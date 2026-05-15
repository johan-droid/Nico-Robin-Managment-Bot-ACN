from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from telegram import Bot, ChatPermissions, Update
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes

from database import async_session_factory
from services.acn_service import acn_only, admin_captain_commander_only
from services.audit_service import AuditService
from services.event_service import emit_user_action
from services.group_service import GroupService
from services.user_service import UserService
from services.warn_service import WarnService
from utils.decorators import admin_only, group_only
from utils.formatters import (
    ban_message,
    display_user,
    mute_message,
    telegram_user_label,
    warn_message,
)
from utils.i18n import gettext
from utils.permissions import is_telegram_admin
from utils.time import human_duration, parse_duration, until_datetime


@dataclass(frozen=True)
class TargetUser:
    user_id: int
    label: str
    consumed_args: int


async def resolve_target(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> TargetUser | None:
    message = update.effective_message
    if message and message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        return TargetUser(target.id, telegram_user_label(target), 0)

    args = context.args or []
    if not args:
        return None
    raw = args[0].strip()
    async with async_session_factory() as session:
        async with session.begin():
            if raw.startswith("@"):
                user = await UserService.find_by_username(session, raw)
                if user:
                    return TargetUser(
                        user.user_id,
                        display_user(user.user_id, user.username),
                        1,
                    )
            numeric = raw.removeprefix("@")
            if numeric.lstrip("-").isdigit():
                user_id = int(numeric)
                return TargetUser(user_id, display_user(user_id), 1)
    return None


def reason_from_args(
    args: list[str], start: int, default: str = "No reason provided"
) -> str:
    reason = " ".join(args[start:]).strip()
    return reason or default


async def _record_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    target: TargetUser,
    reason: str | None = None,
) -> None:
    chat = update.effective_chat
    actor = update.effective_user
    if chat is None:
        return
    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)
            if actor:
                await UserService.ensure_user(session, actor)
            await UserService.ensure_minimal_user(session, target.user_id)
            await AuditService.log_action(
                session=session,
                group_id=chat.id,
                action=action,
                actor_id=actor.id if actor else None,
                target_id=target.user_id,
                reason=reason,
            )
        await AuditService.forward_action(
            context=context,
            group=group,
            action=action,
            actor_label=telegram_user_label(actor),
            target_label=target.label,
            reason=reason,
        )


async def _apply_mute(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    duration: timedelta | None,
) -> None:
    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_datetime(duration),
    )


async def _apply_unmute(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> None:
    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        ),
    )


@acn_only
@admin_captain_commander_only
async def ban(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    target = await resolve_target(update, context)
    if target is None:
        await msg.reply_text(
            "🌸 Please specify a user to ban.\n"
            "Usage: `/ban @username` or reply to a message and use `/ban`"
        )
        return

    # Prevent banning admins or the bot itself
    if target.user_id == context.bot.id:
        await msg.reply_text("🌸 I cannot ban myself!")
        return

    try:
        if await is_telegram_admin(context, chat.id, target.user_id):
            await msg.reply_text("🌸 I cannot ban an admin user.")
            return
    except TelegramError:
        pass  # Continue if we can't check admin status

    reason = reason_from_args(context.args or [], target.consumed_args)

    try:
        await context.bot.ban_chat_member(chat.id, target.user_id)
        async with async_session_factory() as session:
            async with session.begin():
                await UserService.ensure_minimal_user(session, target.user_id)
                await UserService.increment_ban_count(session, target.user_id)
        await _record_action(update, context, "ban", target, reason)
        await msg.reply_text(ban_message(target.label, reason))

        # Emit real-time event
        await emit_user_action(
            action="ban",
            user_id=target.user_id,
            group_id=chat.id,
            actor_id=update.effective_user.id if update.effective_user else None,
            reason=reason,
            extra_data={"target_label": target.label},
        )
    except TelegramError as e:
        await msg.reply_text(f"🌸 Failed to ban user: {str(e)}")


@acn_only
@admin_captain_commander_only
async def unban(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    target = await resolve_target(update, context)
    if msg is None or chat is None or target is None:
        if msg:
            await msg.reply_text(gettext("ban.no_target"))
        return
    await context.bot.unban_chat_member(chat.id, target.user_id, only_if_banned=True)
    await _record_action(update, context, "unban", target)
    await msg.reply_text(gettext("unban.success", target=target.label))


@acn_only
@admin_captain_commander_only
async def kick(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    target = await resolve_target(update, context)
    if msg is None or chat is None or target is None:
        if msg:
            await msg.reply_text(gettext("ban.no_target"))
        return
    reason = reason_from_args(context.args or [], target.consumed_args)
    await context.bot.ban_chat_member(chat.id, target.user_id)
    await context.bot.unban_chat_member(chat.id, target.user_id, only_if_banned=True)
    await _record_action(update, context, "kick", target, reason)
    await msg.reply_text(gettext("kick.success", target=target.label, reason=reason))


@group_only
@admin_only
async def mute(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    target = await resolve_target(update, context)
    if msg is None or chat is None or target is None:
        if msg:
            await msg.reply_text(gettext("ban.no_target"))
        return
    args = context.args or []
    duration = parse_duration(
        args[target.consumed_args] if len(args) > target.consumed_args else None
    )
    reason_start = target.consumed_args + (1 if duration else 0)
    reason = reason_from_args(args, reason_start)
    await _apply_mute(context, chat.id, target.user_id, duration)
    await _record_action(update, context, "mute", target, reason)
    await msg.reply_text(mute_message(target.label, human_duration(duration), reason))


@group_only
@admin_only
async def unmute(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    target = await resolve_target(update, context)
    if msg is None or chat is None or target is None:
        if msg:
            await msg.reply_text(gettext("ban.no_target"))
        return
    await _apply_unmute(context, chat.id, target.user_id)
    await _record_action(update, context, "unmute", target)
    await msg.reply_text(gettext("unmute.success", target=target.label))


async def _auto_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    target: TargetUser,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    if action == "ban":
        await context.bot.ban_chat_member(chat.id, target.user_id)
    elif action == "kick":
        await context.bot.ban_chat_member(chat.id, target.user_id)
        await context.bot.unban_chat_member(
            chat.id, target.user_id, only_if_banned=True
        )
    elif action == "mute":
        await _apply_mute(context, chat.id, target.user_id, timedelta(hours=1))


@acn_only
@admin_captain_commander_only
async def warn(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user
    target = await resolve_target(update, context)
    if msg is None or chat is None or target is None:
        if msg:
            await msg.reply_text(gettext("ban.no_target"))
        return
    reason = reason_from_args(context.args or [], target.consumed_args)
    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)
            if actor:
                await UserService.ensure_user(session, actor)
            await UserService.ensure_minimal_user(session, target.user_id)
            warn_record, count = await WarnService.issue_warn(
                session=session,
                group_id=chat.id,
                user_id=target.user_id,
                admin_id=actor.id if actor else None,
                reason=reason,
            )
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action="warn",
                actor_id=actor.id if actor else None,
                target_id=target.user_id,
                reason=reason,
            )
            max_warns = group.max_warns
            warn_action = group.warn_action
            should_auto_action = count >= max_warns
            if should_auto_action:
                await WarnService.mark_latest_auto_action(
                    session,
                    warn_record.warn_id,
                    warn_action,
                )
    await msg.reply_text(warn_message(target.label, count, max_warns, reason))

    # Emit real-time event
    await emit_user_action(
        action="warn",
        user_id=target.user_id,
        group_id=chat.id,
        actor_id=update.effective_user.id if update.effective_user else None,
        reason=reason,
        extra_data={
            "target_label": target.label,
            "warning_count": count,
            "max_warns": max_warns,
        },
    )

    if should_auto_action:
        await _auto_action(update, context, warn_action, target)
        await _record_action(
            update, context, f"warn_limit_{warn_action}", target, reason
        )
        await msg.reply_text(
            gettext("warn.limit_reached", target=target.label, action=warn_action)
        )


@acn_only
@admin_captain_commander_only
async def warns(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    target = await resolve_target(update, context)
    if msg is None or chat is None:
        return
    if target is None and update.effective_user:
        target = TargetUser(
            update.effective_user.id,
            telegram_user_label(update.effective_user),
            0,
        )
    if target is None:
        await msg.reply_text(gettext("ban.no_target"))
        return
    async with async_session_factory() as session:
        records = await WarnService.list_active_warns(session, chat.id, target.user_id)
    if not records:
        await msg.reply_text(gettext("warn.none"))
        return
    lines = [f"🌸 Active warnings for {target.label}:"]
    lines.extend(f"{item.warn_id}. {item.reason}" for item in records)
    await msg.reply_text("\n".join(lines))


@acn_only
@admin_captain_commander_only
async def resetwarn(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    target = await resolve_target(update, context)
    if msg is None or chat is None or target is None:
        if msg:
            await msg.reply_text(gettext("ban.no_target"))
        return
    async with async_session_factory() as session:
        async with session.begin():
            count = await WarnService.reset_warns(session, chat.id, target.user_id)
            await AuditService.log_action(
                session,
                group_id=chat.id,
                action="resetwarn",
                actor_id=update.effective_user.id if update.effective_user else None,
                target_id=target.user_id,
            )
    await msg.reply_text(gettext("warn.reset", count=count, target=target.label))


@group_only
@admin_only
async def pin(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    del context
    msg = update.effective_message
    if msg is None or msg.reply_to_message is None:
        if msg:
            await msg.reply_text("🌸 Reply to the page you want pinned.")
        return
    await msg.reply_to_message.pin(disable_notification=True)
    await msg.reply_text("🌸 Pinned. A useful page should be easy to find.")


@group_only
@admin_only
async def delete_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    del context
    msg = update.effective_message
    if msg is None or msg.reply_to_message is None:
        return
    try:
        await msg.reply_to_message.delete()
        await msg.delete()
    except TelegramError:
        await msg.reply_text("🌸 That page resisted removal.")


@group_only
@admin_only
async def slowmode(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Coroutine[Any, Any, None]:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    try:
        delay = int((context.args or ["0"])[0])
    except ValueError:
        await msg.reply_text("🌸 Give me a number of seconds to inscribe.")
        return
    from typing import cast

    await cast(Bot, context.bot).set_chat_slow_mode_delay(
        chat_id=chat.id, slow_mode_delay=delay
    )
    await msg.reply_text(f"🌸 Slow mode set to {delay} seconds.")


def register(app) -> None:
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warns", warns))
    app.add_handler(CommandHandler("resetwarn", resetwarn))
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("del", delete_message))
    app.add_handler(CommandHandler("slowmode", slowmode))

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command, require_admin

MODULE_NAME = "moderation"


def _parse_target(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> tuple[int | None, str | None]:
    msg = update.effective_message
    if msg is None:
        return None, None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        user = msg.reply_to_message.from_user
        return user.id, user.full_name
    if not context.args:
        return None, None
    raw = context.args[0].strip()
    if raw.lstrip("-").isdigit():
        return int(raw), raw
    return None, None


def _parse_reason(context: ContextTypes.DEFAULT_TYPE, start_index: int = 1) -> str:
    if not context.args or len(context.args) <= start_index:
        return "No reason provided"
    return " ".join(context.args[start_index:]).strip() or "No reason provided"


def _parse_duration_seconds(value: str | None) -> int:
    if not value:
        return 3600
    normalized = value.lower().strip()
    if normalized.isdigit():
        return int(normalized) * 60
    if normalized.endswith("m") and normalized[:-1].isdigit():
        return int(normalized[:-1]) * 60
    if normalized.endswith("h") and normalized[:-1].isdigit():
        return int(normalized[:-1]) * 3600
    if normalized.endswith("d") and normalized[:-1].isdigit():
        return int(normalized[:-1]) * 86400
    return 3600


async def _warn_count_get(
    context: ContextTypes.DEFAULT_TYPE,
    group_id: int,
    user_id: int,
) -> int:
    cache = context.application.bot_data["cache"]
    db = context.application.bot_data["db"]
    key = f"warn:{group_id}:{user_id}"
    cached = cache.get(key)
    if cached is not None:
        return int(cached)
    row = await db.fetchone(
        "SELECT warn_count FROM warns WHERE group_id = ? AND user_id = ?",
        (group_id, user_id),
    )
    count = int(row["warn_count"]) if row else 0
    cache.set(key, count, ttl=600)
    return count


async def _warn_count_set(
    context: ContextTypes.DEFAULT_TYPE,
    group_id: int,
    user_id: int,
    count: int,
    reason: str | None = None,
) -> None:
    cache = context.application.bot_data["cache"]
    db = context.application.bot_data["db"]
    cache.set(f"warn:{group_id}:{user_id}", count, ttl=600)
    await db.execute(
        """
        INSERT INTO warns (group_id, user_id, warn_count, last_reason, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(group_id, user_id)
        DO UPDATE SET warn_count = excluded.warn_count, last_reason = excluded.last_reason, updated_at = excluded.updated_at
        """,
        (group_id, user_id, count, reason, int(time.time())),
    )


async def _log_action(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    action_type: str,
    moderator_id: int,
    target_id: int | None,
    group_id: int,
    reason: str | None,
) -> None:
    db = context.application.bot_data["db"]
    await db.log_moderation(
        action_type=action_type,
        moderator_id=moderator_id,
        target_id=target_id,
        group_id=group_id,
        reason=reason,
    )


@log_command
@require_admin
@feature_toggle("moderation")
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text(
            "Reply to a user or pass a numeric user id: /ban <user_id> [reason]"
        )
        return

    reason = _parse_reason(context)
    await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_id)
    await _log_action(
        context,
        action_type="ban",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=reason,
    )
    await msg.reply_text(f"Banned {target_label or target_id}. Reason: {reason}")


@log_command
@require_admin
@feature_toggle("moderation")
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /unban <user_id>")
        return
    await context.bot.unban_chat_member(
        chat_id=chat.id, user_id=target_id, only_if_banned=True
    )
    await _log_action(
        context,
        action_type="unban",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=None,
    )
    await msg.reply_text(f"Unbanned {target_label or target_id}.")


@log_command
@require_admin
@feature_toggle("moderation")
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /kick <user_id> [reason]")
        return
    reason = _parse_reason(context)
    await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_id)
    await context.bot.unban_chat_member(
        chat_id=chat.id, user_id=target_id, only_if_banned=True
    )
    await _log_action(
        context,
        action_type="kick",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=reason,
    )
    await msg.reply_text(f"Kicked {target_label or target_id}. Reason: {reason}")


@log_command
@require_admin
@feature_toggle("moderation")
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /mute <user_id> [30m|2h|1d] [reason]")
        return

    duration_raw = context.args[1] if len(context.args) > 1 else None
    duration_seconds = _parse_duration_seconds(duration_raw)
    until_date = datetime.utcnow() + timedelta(seconds=duration_seconds)
    reason = _parse_reason(context, start_index=2)
    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=target_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date,
    )
    await _log_action(
        context,
        action_type="mute",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=reason,
    )
    await msg.reply_text(
        f"Muted {target_label or target_id} for {duration_seconds // 60} minutes."
    )


@log_command
@require_admin
@feature_toggle("moderation")
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /unmute <user_id>")
        return
    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=target_id,
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
            can_invite_users=True,
        ),
    )
    await _log_action(
        context,
        action_type="unmute",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=None,
    )
    await msg.reply_text(f"Unmuted {target_label or target_id}.")


@log_command
@require_admin
@feature_toggle("moderation")
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /warn <user_id> [reason]")
        return
    reason = _parse_reason(context)
    current = await _warn_count_get(context, chat.id, target_id)
    new_count = current + 1
    await _warn_count_set(context, chat.id, target_id, new_count, reason=reason)
    await _log_action(
        context,
        action_type="warn",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=reason,
    )
    await msg.reply_text(
        f"{target_label or target_id} has {new_count} warning(s). Reason: {reason}"
    )


@log_command
@require_admin
@feature_toggle("moderation")
async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None and update.effective_user:
        target_id = update.effective_user.id
        target_label = update.effective_user.full_name
    if target_id is None:
        await msg.reply_text("Usage: /warns <user_id>")
        return
    count = await _warn_count_get(context, chat.id, target_id)
    await msg.reply_text(f"{target_label or target_id} has {count} warning(s).")


@log_command
@require_admin
@feature_toggle("moderation")
async def resetwarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or msg is None or user is None:
        return
    target_id, target_label = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /resetwarn <user_id>")
        return
    await _warn_count_set(context, chat.id, target_id, 0, reason="reset")
    await _log_action(
        context,
        action_type="resetwarn",
        moderator_id=user.id,
        target_id=target_id,
        group_id=chat.id,
        reason=None,
    )
    await msg.reply_text(f"Warnings reset for {target_label or target_id}.")


@log_command
@require_admin
@feature_toggle("moderation")
async def slowmode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or msg is None or user is None:
        return
    if not context.args or not context.args[0].isdigit():
        await msg.reply_text("Usage: /slowmode <seconds>")
        return
    seconds = max(0, min(3600, int(context.args[0])))
    await context.bot.set_chat_slow_mode_delay(chat_id=chat.id, slow_mode_delay=seconds)
    await _log_action(
        context,
        action_type="slowmode",
        moderator_id=user.id,
        target_id=None,
        group_id=chat.id,
        reason=f"{seconds}s",
    )
    await msg.reply_text(f"Slow mode set to {seconds} seconds.")


@log_command
@feature_toggle("moderation")
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    if msg.reply_to_message is None or msg.reply_to_message.from_user is None:
        await msg.reply_text("Reply to a message with /report [reason].")
        return

    db = context.application.bot_data["db"]
    reason = _parse_reason(context, start_index=0)
    report_id = await db.execute_returning_id(
        """
        INSERT INTO reports (group_id, message_id, reporter_id, target_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            chat.id,
            msg.reply_to_message.message_id,
            user.id,
            msg.reply_to_message.from_user.id,
            reason,
            int(time.time()),
        ),
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Acknowledge", callback_data=f"report_ack:{report_id}"
                ),
                InlineKeyboardButton(
                    "Dismiss", callback_data=f"report_dis:{report_id}"
                ),
            ]
        ]
    )
    await msg.reply_text(
        f"Report #{report_id} created for admin review.",
        reply_markup=keyboard,
    )


async def _can_handle_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    db = context.application.bot_data["db"]
    role = await db.get_user_role(user_id)
    if role in {"Captain", "Commander"}:
        return True
    admin_cache = context.application.bot_data["admin_cache"]
    await admin_cache.remember_group(chat.id)
    return await admin_cache.is_admin(context.bot, chat.id, user_id)


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None or query.from_user is None:
        return
    if not query.data.startswith("report_"):
        return
    await query.answer()

    if not await _can_handle_report(update, context, query.from_user.id):
        await query.edit_message_text(
            "Only admins, commanders, or captains can handle reports."
        )
        return

    action, report_id_raw = query.data.split(":")
    report_id = int(report_id_raw)
    db = context.application.bot_data["db"]
    row = await db.fetchone(
        "SELECT status FROM reports WHERE report_id = ?", (report_id,)
    )
    if row is None:
        await query.edit_message_text("This report no longer exists.")
        return
    if row["status"] != "pending":
        await query.edit_message_text(f"Report #{report_id} is already handled.")
        return

    new_status = "acknowledged" if action == "report_ack" else "dismissed"
    await db.execute(
        """
        UPDATE reports
        SET status = ?, handled_by = ?, handled_at = ?
        WHERE report_id = ?
        """,
        (new_status, query.from_user.id, int(time.time()), report_id),
    )
    await query.edit_message_text(f"Report #{report_id} {new_status}.")


def _group_only_filter(
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Any],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]:
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if chat is None or chat.type not in {"group", "supergroup"}:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "This command is for group chats."
                )
            return
        await func(update, context)

    return wrapper


def register(application) -> None:
    application.add_handler(CommandHandler("ban", _group_only_filter(ban)))
    application.add_handler(CommandHandler("unban", _group_only_filter(unban)))
    application.add_handler(CommandHandler("kick", _group_only_filter(kick)))
    application.add_handler(CommandHandler("mute", _group_only_filter(mute)))
    application.add_handler(CommandHandler("unmute", _group_only_filter(unmute)))
    application.add_handler(CommandHandler("warn", _group_only_filter(warn)))
    application.add_handler(CommandHandler("warns", _group_only_filter(warns)))
    application.add_handler(CommandHandler("resetwarn", _group_only_filter(resetwarn)))
    application.add_handler(CommandHandler("slowmode", _group_only_filter(slowmode)))
    application.add_handler(CommandHandler("report", _group_only_filter(report)))
    application.add_handler(
        CallbackQueryHandler(report_callback, pattern=r"^report_(ack|dis):\d+$")
    )

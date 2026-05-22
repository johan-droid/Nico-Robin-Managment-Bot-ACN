from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatPermissions
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command, require_admin

MODULE_NAME = "moderation"

FULL_PERMISSIONS = ChatPermissions(
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
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
)

NO_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_invite_users=True,
)


def _db(context: ContextTypes.DEFAULT_TYPE):
    return get_runtime(context)["db"]


async def _log_moderation(context: ContextTypes.DEFAULT_TYPE, action_type: str, moderator_id: int | None, target_id: int | None, group_id: int | None, reason: str | None) -> None:
    await _db(context).execute(
        """
        INSERT INTO moderation_log (action_type, moderator_id, target_id, group_id, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (action_type, moderator_id, target_id, group_id, reason),
    )


async def _resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[int | None, str]:
    message = update.effective_message
    if message is None:
        return None, ""

    args = context.args or []
    if message.reply_to_message and message.reply_to_message.from_user:
        reason = " ".join(args) if args else ""
        return message.reply_to_message.from_user.id, reason

    if args:
        try:
            target_id = int(args[0])
            return target_id, " ".join(args[1:]) if len(args) > 1 else ""
        except ValueError:
            return None, ""

    return None, ""


@feature_toggle("moderation")
@require_admin
@log_command
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    await context.bot.ban_chat_member(chat.id, target_id)
    await _log_moderation(context, "ban", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Banned {target_id}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    await context.bot.unban_chat_member(chat.id, target_id, only_if_banned=False)
    await _log_moderation(context, "unban", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Unbanned {target_id}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    await context.bot.ban_chat_member(chat.id, target_id)
    await _log_moderation(context, "kick", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Kicked {target_id}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    await context.bot.restrict_chat_member(chat.id, target_id, permissions=NO_PERMISSIONS)
    await _log_moderation(context, "mute", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Muted {target_id}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    await context.bot.restrict_chat_member(chat.id, target_id, permissions=FULL_PERMISSIONS)
    await _log_moderation(context, "unmute", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Unmuted {target_id}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    db = _db(context)
    row = await db.fetchone("SELECT warnings FROM warnings WHERE group_id = ? AND user_id = ?", (chat.id, target_id))
    warnings = int(row[0]) + 1 if row else 1
    await db.execute(
        """
        INSERT INTO warnings (group_id, user_id, warnings, last_warned_at)
        VALUES (?, ?, ?, strftime('%s','now'))
        ON CONFLICT(group_id, user_id) DO UPDATE SET warnings = excluded.warnings, last_warned_at = excluded.last_warned_at
        """,
        (chat.id, target_id, warnings),
    )
    await _log_moderation(context, "warn", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Warning issued to {target_id}. Total warnings: {warnings}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, _ = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    row = await _db(context).fetchone("SELECT warnings FROM warnings WHERE group_id = ? AND user_id = ?", (chat.id, target_id))
    await message.reply_text(f"🌸 {target_id} has {int(row[0]) if row else 0} warnings.")


@feature_toggle("moderation")
@require_admin
@log_command
async def resetwarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    target_id, reason = await _resolve_target(update, context)
    if target_id is None:
        await message.reply_text("🌸 Reply to a user or provide a user ID.")
        return
    await _db(context).execute("DELETE FROM warnings WHERE group_id = ? AND user_id = ?", (chat.id, target_id))
    await _log_moderation(context, "resetwarn", update.effective_user.id if update.effective_user else None, target_id, chat.id, reason)
    await message.reply_text(f"🌸 Warnings cleared for {target_id}.")


@feature_toggle("moderation")
@require_admin
@log_command
async def slowmode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /slowmode <seconds>")
        return
    seconds = int(args[0])
    await context.bot.set_chat_slow_mode_delay(chat.id, seconds)
    await _log_moderation(context, "slowmode", update.effective_user.id if update.effective_user else None, None, chat.id, str(seconds))
    await message.reply_text(f"🌸 Slow mode set to {seconds} seconds.")


@log_command
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return

    target_id = message.reply_to_message.from_user.id if message.reply_to_message and message.reply_to_message.from_user else None
    reason = " ".join(context.args or []) or "No reason provided"
    existing = await _db(context).fetchone(
        "SELECT report_id FROM reports WHERE group_id = ? AND reporter_id = ? AND target_id IS ? AND reason = ? AND status = 'pending'",
        (chat.id, user.id, target_id, reason),
    )
    if existing:
        await message.reply_text(f"🌸 Report already pending (#{existing[0]}).")
        return

    report_id = await _db(context).execute(
        """
        INSERT INTO reports (group_id, reporter_id, target_id, target_message_id, reason, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """,
        (
            chat.id,
            user.id,
            target_id,
            message.reply_to_message.message_id if message.reply_to_message else None,
            reason,
        ),
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Acknowledge", callback_data=f"report:ack:{report_id}"),
            InlineKeyboardButton("Dismiss", callback_data=f"report:dismiss:{report_id}"),
        ]
    ])
    await message.reply_text(f"🌸 Report submitted #{report_id}.", reply_markup=keyboard)


async def handle_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    _, action, report_id_text = query.data.split(":", 2)
    report_id = int(report_id_text)
    row = await _db(context).fetchone("SELECT status FROM reports WHERE report_id = ?", (report_id,))
    if row is None:
        await query.answer("Report not found.", show_alert=True)
        return
    if row[0] != "pending":
        await query.answer("Report already handled.", show_alert=True)
        return
    new_status = "acknowledged" if action == "ack" else "dismissed"
    await _db(context).execute(
        "UPDATE reports SET status = ?, handled_by = ?, handled_at = CURRENT_TIMESTAMP WHERE report_id = ?",
        (new_status, query.from_user.id, report_id),
    )
    await query.answer(f"Report {new_status}.")
    if query.message is not None:
        await query.message.edit_text(f"🌸 Report #{report_id} {new_status} by {query.from_user.full_name}.")


def register(application) -> None:
    application.add_handler(CommandHandler("ban", ban, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("unban", unban, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("kick", kick, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("mute", mute, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("unmute", unmute, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("warn", warn, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("warns", warns, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("resetwarn", resetwarn, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("slowmode", slowmode, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("report", report, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CallbackQueryHandler(handle_report_action, pattern=r"^report:(ack|dismiss):\d+$"))

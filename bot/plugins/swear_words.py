from __future__ import annotations

import asyncio

from telegram import ChatPermissions, Update
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes, MessageHandler
from telegram.ext import filters as tg_filters

from database import async_session_factory
from services.audit_service import AuditService
from services.group_service import GroupService
from services.swear_word_service import PunishmentResult, SwearWordService
from utils.decorators import admin_only, group_only
from utils.time import human_duration


def _parse_duration(duration_str: str) -> int:
    """Parse duration string like '1h', '30m', '1d' into seconds"""
    if not duration_str:
        return 300  # Default 5 minutes

    duration_str = duration_str.lower().strip()

    # Direct number (assume seconds)
    if duration_str.isdigit():
        return int(duration_str)

    # Parse with units
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    for unit, multiplier in units.items():
        if duration_str.endswith(unit):
            try:
                number = int(duration_str[:-1])
                return number * multiplier
            except ValueError:
                break

    return 300  # Default if parsing fails


def _swear_help() -> str:
    return (
        "🌸 Swear Word Management Commands:\n"
        "/addswear <word> [severity] [punishment] [duration] - Add swear word\n"
        "/delswear <word> - Remove swear word\n"
        "/swearlist - List all swear words\n"
        "/swearsettings [severity] [punishment] [duration] - Set defaults\n\n"
        "Severity: mild, moderate, severe\n"
        "Punishment: mute, temp_ban, perm_ban\n"
        "Duration: number (seconds) or 1h, 30m, 1d\n\n"
        "Examples:\n"
        "/addswear damn mild mute 10m\n"
        "/addswear f*ck severe temp_ban 1d\n"
        "/swearsettings moderate mute 30m"
    )


@group_only
@admin_only
async def add_swear_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(_swear_help())
        return

    word = args[0].strip()
    severity = args[1] if len(args) > 1 else "moderate"
    punishment = args[2] if len(args) > 2 else "mute"
    duration_str = args[3] if len(args) > 3 else "5m"

    # Validate inputs
    if severity not in SwearWordService.VALID_SEVERITIES:
        await msg.reply_text(
            f"🌸 Invalid severity '{severity}'. Valid: {', '.join(SwearWordService.VALID_SEVERITIES)}"
        )
        return

    if punishment not in SwearWordService.VALID_PUNISHMENTS:
        await msg.reply_text(
            f"🌸 Invalid punishment '{punishment}'. Valid: {', '.join(SwearWordService.VALID_PUNISHMENTS)}"
        )
        return

    duration = _parse_duration(duration_str)
    if punishment == "perm_ban" and duration > 0:
        duration = 0  # Permanent ban has no duration

    try:
        async with async_session_factory() as session:
            async with session.begin():
                await GroupService.ensure_group(session, chat)
                await SwearWordService.add_swear_word(
                    session=session,
                    group_id=chat.id,
                    word=word,
                    severity=severity,
                    punishment_type=punishment,
                    duration=duration,
                    created_by=(
                        update.effective_user.id if update.effective_user else None
                    ),
                )

        duration_text = f" for {human_duration(duration)}" if duration > 0 else ""
        await msg.reply_text(
            f"🌸 Added swear word '{word}' ({severity}) - {punishment}{duration_text}"
        )

        # Log the action
        await AuditService.log_action(
            session=session,
            group_id=chat.id,
            action="add_swear_word",
            actor_id=update.effective_user.id if update.effective_user else None,
            target_id=None,
            reason=f"Added swear word: {word} ({severity})",
            extra={
                "word": word,
                "severity": severity,
                "punishment": punishment,
                "duration": duration,
            },
        )

    except Exception as e:
        await msg.reply_text(f"🌸 Error adding swear word: {str(e)}")


@group_only
@admin_only
async def remove_swear_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text("🌸 Usage: /delswear <word>")
        return

    word = args[0].strip()

    try:
        async with async_session_factory() as session:
            async with session.begin():
                deleted_count = await SwearWordService.remove_swear_word(
                    session, chat.id, word
                )

        if deleted_count > 0:
            await msg.reply_text(f"🌸 Removed swear word '{word}'")

            # Log the action
            await AuditService.log_action(
                session=session,
                group_id=chat.id,
                action="remove_swear_word",
                actor_id=update.effective_user.id if update.effective_user else None,
                target_id=None,
                reason=f"Removed swear word: {word}",
                extra={"word": word},
            )
        else:
            await msg.reply_text(f"🌸 Swear word '{word}' not found")

    except Exception as e:
        await msg.reply_text(f"🌸 Error removing swear word: {str(e)}")


@group_only
@admin_only
async def list_swear_words(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    try:
        async with async_session_factory() as session:
            swear_words = await SwearWordService.list_swear_words(session, chat.id)

        if not swear_words:
            await msg.reply_text("🌸 No swear words configured for this group")
            return

        response = "🌸 **Swear Words List:**\n\n"
        for swear_word in swear_words:
            duration_text = (
                f" ({human_duration(swear_word.duration)})"
                if swear_word.duration > 0
                else ""
            )
            response += f"• `{swear_word.word}` - {swear_word.severity} - {swear_word.punishment}{duration_text}\n"

        await msg.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await msg.reply_text(f"🌸 Error listing swear words: {str(e)}")


@group_only
@admin_only
async def swear_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []

    # Show current settings if no arguments
    if len(args) == 0:
        try:
            async with async_session_factory() as session:
                await GroupService.ensure_group(session, chat)
                group = await GroupService.get_group(session, chat.id)
                if group is None:
                    await msg.reply_text(
                        "🌸 Swear word settings are not available yet."
                    )
                    return

            duration_text = (
                f" ({human_duration(group.default_swear_duration)})"
                if group.default_swear_duration > 0
                else ""
            )
            await msg.reply_text(
                f"🌸 **Current Swear Word Settings:**\n\n"
                f"• Enabled: {'Yes' if group.swear_words_enabled else 'No'}\n"
                f"• Default Severity: {group.default_swear_severity}\n"
                f"• Default Punishment: {group.default_swear_punishment}{duration_text}"
            )
        except Exception as e:
            await msg.reply_text(f"🌸 Error getting settings: {str(e)}")
        return

    # Update settings
    severity = args[0] if len(args) > 0 else "moderate"
    punishment = args[1] if len(args) > 1 else "mute"
    duration_str = args[2] if len(args) > 2 else "5m"

    # Validate inputs
    if severity not in SwearWordService.VALID_SEVERITIES:
        await msg.reply_text(
            f"🌸 Invalid severity '{severity}'. Valid: {', '.join(SwearWordService.VALID_SEVERITIES)}"
        )
        return

    if punishment not in SwearWordService.VALID_PUNISHMENTS:
        await msg.reply_text(
            f"🌸 Invalid punishment '{punishment}'. Valid: {', '.join(SwearWordService.VALID_PUNISHMENTS)}"
        )
        return

    duration = _parse_duration(duration_str)
    if punishment == "perm_ban" and duration > 0:
        duration = 0

    try:
        async with async_session_factory() as session:
            async with session.begin():
                await GroupService.ensure_group(session, chat)
                await GroupService.update_settings(
                    session,
                    chat.id,
                    default_swear_severity=severity,
                    default_swear_punishment=punishment,
                    default_swear_duration=duration,
                )

            group = await GroupService.get_group(session, chat.id)
            if group is None:
                await msg.reply_text(
                    "🌸 Swear word settings were saved, but I could not reload them."
                )
                return

        duration_text = f" ({human_duration(duration)})" if duration > 0 else ""
        await msg.reply_text(
            f"🌸 Updated default settings: {severity} - {punishment}{duration_text}"
        )

        # Log the action
        await AuditService.log_action(
            session=session,
            group_id=chat.id,
            action="swear_settings",
            actor_id=update.effective_user.id if update.effective_user else None,
            target_id=None,
            reason="Updated swear word settings",
            extra={
                "severity": severity,
                "punishment": punishment,
                "duration": duration,
            },
        )

    except Exception as e:
        await msg.reply_text(f"🌸 Error updating settings: {str(e)}")


async def _apply_punishment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    punishment: PunishmentResult,
) -> None:
    """Apply the calculated punishment to the user"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return

    try:
        if punishment.action == "mute":
            await context.bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            # Schedule unmute if duration > 0
            if punishment.duration > 0:
                context.application.create_task(
                    _schedule_unmute(context, chat.id, user.id, punishment.duration)
                )

        elif punishment.action == "temp_ban":
            await context.bot.ban_chat_member(chat.id, user.id)
            # Schedule unban if duration > 0
            if punishment.duration > 0:
                context.application.create_task(
                    _schedule_unban(context, chat.id, user.id, punishment.duration)
                )

        elif punishment.action == "perm_ban":
            await context.bot.ban_chat_member(chat.id, user.id)

    except TelegramError as e:
        await msg.reply_text(f"🌸 Failed to apply punishment: {str(e)}")


async def _schedule_unmute(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, duration: int
) -> None:
    """Schedule unmute after duration"""
    await asyncio.sleep(duration)
    try:
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(can_send_messages=True),
        )
    except Exception:
        pass  # User might have left the group


async def _schedule_unban(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, duration: int
) -> None:
    """Schedule unban after duration"""
    await asyncio.sleep(duration)
    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    except Exception:
        pass  # User might have left the group


async def handle_swear_words(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle swear word detection in messages"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None or user.is_bot or not msg.text:
        return

    try:
        async with async_session_factory() as session:
            async with session.begin():
                # Check if swear words are enabled for this group
                group = await GroupService.get_group(session, chat.id)
                if not group.swear_words_enabled:
                    return

                # Check if user is admin
                from utils.permissions import is_telegram_admin

                if await is_telegram_admin(context, chat.id, user.id):
                    return

                # Match swear words
                matches = await SwearWordService.match_swear_words(
                    session, chat.id, msg.text
                )
                if not matches:
                    return

                # Use the highest severity match
                highest_match = max(
                    matches,
                    key=lambda m: (
                        0
                        if m.severity == "mild"
                        else 1 if m.severity == "moderate" else 2
                    ),
                )

                # Calculate punishment
                punishment = await SwearWordService.calculate_punishment(
                    session, chat.id, user.id, highest_match
                )

                # Apply punishment
                await _apply_punishment(update, context, punishment)

                # Record violation
                await SwearWordService.record_violation(
                    session, chat.id, user.id, highest_match, punishment
                )

                # Log action
                await AuditService.log_action(
                    session=session,
                    group_id=chat.id,
                    action="swear_word_violation",
                    actor_id=None,
                    target_id=user.id,
                    reason=punishment.reason,
                    extra={
                        "word": highest_match.matched_text,
                        "severity": highest_match.severity,
                        "punishment": punishment.action,
                        "duration": punishment.duration,
                        "escalate": punishment.escalate,
                    },
                )

                # Notify user
                escalate_text = " (escalated)" if punishment.escalate else ""
                await msg.reply_text(
                    f"🌸 Swear word detected! {punishment.reason}{escalate_text}"
                )

    except Exception as e:
        # Log error but don't crash
        print(f"Error handling swear words: {e}")


def register(app) -> None:
    app.add_handler(CommandHandler("addswear", add_swear_word))
    app.add_handler(CommandHandler("delswear", remove_swear_word))
    app.add_handler(CommandHandler("swearlist", list_swear_words))
    app.add_handler(CommandHandler("swearsettings", swear_settings))
    app.add_handler(
        MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, handle_swear_words),
        group=15,  # Run before general filters but after AI moderation
    )

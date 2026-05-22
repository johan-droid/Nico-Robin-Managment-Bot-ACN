from __future__ import annotations

import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import (
    feature_toggle,
    log_command,
    require_commander_or_captain,
)

MODULE_NAME = "acn"


def _parse_user_id_or_reply(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int | None:
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id
    if context.args and context.args[0].lstrip("-").isdigit():
        return int(context.args[0])
    return None


@log_command
@require_commander_or_captain
@feature_toggle("acn")
async def addacn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    actor = update.effective_user
    if msg is None or actor is None:
        return
    user_id = _parse_user_id_or_reply(update, context)
    if user_id is None:
        await msg.reply_text("Usage: /addacn <user_id> [Member|Commander|Captain]")
        return
    role = context.args[1] if len(context.args) > 1 else "Member"
    role = role.capitalize()
    if role not in {"Member", "Commander", "Captain"}:
        await msg.reply_text("Role must be Member, Commander, or Captain.")
        return
    db = context.application.bot_data["db"]
    await db.execute(
        """
        INSERT INTO acn_whitelist (user_id, username, role, added_by, added_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET role = excluded.role, added_by = excluded.added_by, added_at = excluded.added_at
        """,
        (user_id, None, role, actor.id, int(time.time())),
    )
    context.application.bot_data["cache"].delete(f"role:{user_id}")
    await msg.reply_text(f"User {user_id} added to ACN as {role}.")


@log_command
@require_commander_or_captain
@feature_toggle("acn")
async def removeacn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    user_id = _parse_user_id_or_reply(update, context)
    if user_id is None:
        await msg.reply_text("Usage: /removeacn <user_id>")
        return
    db = context.application.bot_data["db"]
    await db.execute("DELETE FROM acn_whitelist WHERE user_id = ?", (user_id,))
    context.application.bot_data["cache"].delete(f"role:{user_id}")
    await msg.reply_text(f"User {user_id} removed from ACN.")


@log_command
@require_commander_or_captain
@feature_toggle("acn")
async def award(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    if len(context.args) < 2 or not context.args[1].lstrip("-").isdigit():
        await msg.reply_text("Usage: /award <user_id> <points> [reason]")
        return
    target_id = int(context.args[0])
    points = int(context.args[1])
    reason = " ".join(context.args[2:]) if len(context.args) > 2 else "manual_award"
    event_bus = context.application.bot_data["event_bus"]
    await event_bus.publish(
        "points:add",
        {
            "user_id": target_id,
            "points": points,
            "reason": reason,
        },
    )
    db = context.application.bot_data["db"]
    await db.log_moderation(
        action_type="award_points",
        moderator_id=user.id,
        target_id=target_id,
        group_id=update.effective_chat.id if update.effective_chat else 0,
        reason=f"{points} ({reason})",
    )
    await msg.reply_text(f"Awarded {points} points to {target_id}.")


@log_command
@feature_toggle("acn")
async def acn_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    db = context.application.bot_data["db"]
    role = await db.get_user_role(user.id)
    role_text = role if role else "Not whitelisted"
    await msg.reply_text(f"ACN role: {role_text}")


def register(application) -> None:
    application.add_handler(CommandHandler("addacn", addacn))
    application.add_handler(CommandHandler("removeacn", removeacn))
    application.add_handler(CommandHandler("award", award))
    application.add_handler(CommandHandler("acn_status", acn_status))

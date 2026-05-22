from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import get_runtime, log_command, require_commander_or_captain

MODULE_NAME = "acn"


@require_commander_or_captain
@log_command
async def addacn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    if len(args) < 2:
        await message.reply_text("🌸 Usage: /addacn <user_id> <Captain|Commander|Member>")
        return
    user_id = int(args[0])
    role = args[1].title()
    username = args[2] if len(args) > 2 else None
    if role not in {"Captain", "Commander", "Member"}:
        await message.reply_text("🌸 Role must be Captain, Commander, or Member.")
        return
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO acn_whitelist (user_id, username, role, added_by)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username = excluded.username, role = excluded.role, added_by = excluded.added_by, added_at = CURRENT_TIMESTAMP
        """,
        (user_id, username, role, update.effective_user.id if update.effective_user else None),
    )
    if role == "Captain":
        await db.execute("INSERT OR IGNORE INTO captains (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.execute("DELETE FROM commanders WHERE user_id = ?", (user_id,))
    elif role == "Commander":
        await db.execute("INSERT OR IGNORE INTO commanders (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.execute("DELETE FROM captains WHERE user_id = ?", (user_id,))
    await message.reply_text(f"🌸 Added ACN member {user_id} as {role}.")


@require_commander_or_captain
@log_command
async def removeacn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /removeacn <user_id>")
        return
    user_id = int(args[0])
    db = get_runtime(context)["db"]
    await db.execute("DELETE FROM acn_whitelist WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM captains WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM commanders WHERE user_id = ?", (user_id,))
    await message.reply_text(f"🌸 Removed ACN member {user_id}.")


@require_commander_or_captain
@log_command
async def award(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    args = context.args or []
    if len(args) < 2:
        await message.reply_text("🌸 Usage: /award <user_id> <points> [reason]")
        return
    target_id = int(args[0])
    points = int(args[1])
    reason = " ".join(args[2:]) if len(args) > 2 else "ACN reward"
    await get_runtime(context)["event_bus"].publish(
        "points:add",
        {"user_id": target_id, "group_id": chat.id, "points": points, "reason": reason, "source": "acn_award", "transaction_uid": f"acn-{chat.id}-{target_id}-{points}-{reason}"},
    )
    await message.reply_text(f"🌸 Award queued for {target_id}.")


@log_command
async def acn_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    db = get_runtime(context)["db"]
    row = await db.fetchone("SELECT role FROM acn_whitelist WHERE user_id = ?", (user.id,))
    points = await db.fetchone("SELECT points, level FROM user_points WHERE user_id = ?", (user.id,))
    role = row[0] if row else "Non-whitelisted"
    point_text = f"{points[0]} pts, level {points[1]}" if points else "0 pts, level 1"
    await message.reply_text(f"🌸 ACN status for {user.full_name}: {role}; {point_text}")


def register(application) -> None:
    application.add_handler(CommandHandler("addacn", addacn, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("removeacn", removeacn, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("award", award, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("acn_status", acn_status, filters=tg_filters.ChatType.GROUPS))

from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command

MODULE_NAME = "notes"


@feature_toggle("notes")
@log_command
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    args = context.args or []
    if len(args) < 2:
        await message.reply_text("🌸 Usage: /save <name> <content>")
        return

    note_name = args[0].lower().strip()
    content = " ".join(args[1:]).strip()
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO notes (group_id, note_name, content, created_by, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(group_id, note_name) DO UPDATE SET
            content = excluded.content,
            created_by = excluded.created_by,
            updated_at = CURRENT_TIMESTAMP
        """,
        (chat.id, note_name, content, update.effective_user.id if update.effective_user else None),
    )
    await message.reply_text(f"🌸 Saved note: {note_name}")


@feature_toggle("notes")
@log_command
async def get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /get <name>")
        return

    note_name = args[0].lower().strip()
    db = get_runtime(context)["db"]
    row = await db.fetchone(
        "SELECT content FROM notes WHERE group_id = ? AND note_name = ?",
        (chat.id, note_name),
    )
    await message.reply_text(row[0] if row else "🌸 Note not found.")


@feature_toggle("notes")
@log_command
async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    db = get_runtime(context)["db"]
    rows = await db.fetchall("SELECT note_name FROM notes WHERE group_id = ? ORDER BY note_name", (chat.id,))
    if not rows:
        await message.reply_text("🌸 No notes saved.")
        return
    await message.reply_text("🌸 Notes: " + ", ".join(row[0] for row in rows))


@feature_toggle("notes")
@log_command
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /clear <name>")
        return

    note_name = args[0].lower().strip()
    db = get_runtime(context)["db"]
    await db.execute("DELETE FROM notes WHERE group_id = ? AND note_name = ?", (chat.id, note_name))
    await message.reply_text(f"🌸 Deleted note: {note_name}")


def register(application) -> None:
    application.add_handler(CommandHandler("save", save, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("get", get, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("notes", notes, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("clear", clear, filters=tg_filters.ChatType.GROUPS))

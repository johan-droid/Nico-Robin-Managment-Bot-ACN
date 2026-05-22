from __future__ import annotations

import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command, require_admin

MODULE_NAME = "notes"


@log_command
@require_admin
@feature_toggle("notes")
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return
    if len(context.args) < 2:
        await msg.reply_text("Usage: /save <name> <content>")
        return
    name = context.args[0].strip().lower()
    content = " ".join(context.args[1:]).strip()
    db = context.application.bot_data["db"]
    await db.execute(
        """
        INSERT INTO notes (group_id, name, content, saved_by, saved_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(group_id, name)
        DO UPDATE SET content = excluded.content, saved_by = excluded.saved_by, saved_at = excluded.saved_at
        """,
        (chat.id, name, content, user.id, int(time.time())),
    )
    await msg.reply_text(f"Note '{name}' saved.")


@log_command
@feature_toggle("notes")
async def get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /get <name>")
        return
    db = context.application.bot_data["db"]
    row = await db.fetchone(
        "SELECT content FROM notes WHERE group_id = ? AND name = ?",
        (chat.id, context.args[0].strip().lower()),
    )
    if row is None:
        await msg.reply_text("Note not found.")
        return
    await msg.reply_text(str(row["content"]))


@log_command
@feature_toggle("notes")
async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    db = context.application.bot_data["db"]
    rows = await db.fetchall(
        "SELECT name FROM notes WHERE group_id = ? ORDER BY name ASC",
        (chat.id,),
    )
    if not rows:
        await msg.reply_text("No notes saved.")
        return
    await msg.reply_text("Notes:\n" + "\n".join(f"- {row['name']}" for row in rows))


@log_command
@require_admin
@feature_toggle("notes")
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /clear <name>")
        return
    db = context.application.bot_data["db"]
    await db.execute(
        "DELETE FROM notes WHERE group_id = ? AND name = ?",
        (chat.id, context.args[0].strip().lower()),
    )
    await msg.reply_text("Note removed.")


def register(application) -> None:
    application.add_handler(CommandHandler("save", save))
    application.add_handler(CommandHandler("get", get))
    application.add_handler(CommandHandler("notes", notes))
    application.add_handler(CommandHandler("clear", clear))

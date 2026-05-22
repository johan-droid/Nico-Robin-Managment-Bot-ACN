from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from core.decorators import feature_toggle, log_command, require_admin

MODULE_NAME = "filters"


@log_command
@require_admin
@feature_toggle("filters")
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if len(context.args) < 2:
        await msg.reply_text("Usage: /filter <keyword> <reply>")
        return
    keyword = context.args[0].strip().lower()
    reply_text = " ".join(context.args[1:]).strip()
    db = context.application.bot_data["db"]
    await db.execute(
        """
        INSERT INTO chat_filters (group_id, keyword, reply_text, action)
        VALUES (?, ?, ?, 'reply')
        ON CONFLICT(group_id, keyword)
        DO UPDATE SET reply_text = excluded.reply_text
        """,
        (chat.id, keyword, reply_text),
    )
    await msg.reply_text(f"Filter '{keyword}' saved.")


@log_command
@require_admin
@feature_toggle("filters")
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /stop <keyword>")
        return
    keyword = context.args[0].strip().lower()
    db = context.application.bot_data["db"]
    await db.execute(
        "DELETE FROM chat_filters WHERE group_id = ? AND keyword = ?",
        (chat.id, keyword),
    )
    await msg.reply_text(f"Filter '{keyword}' removed.")


@log_command
@feature_toggle("filters")
async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    db = context.application.bot_data["db"]
    rows = await db.fetchall(
        "SELECT keyword, action FROM chat_filters WHERE group_id = ? ORDER BY keyword",
        (chat.id,),
    )
    if not rows:
        await msg.reply_text("No filters configured.")
        return
    lines = ["Filters:"]
    lines.extend(f"- {row['keyword']} ({row['action']})" for row in rows)
    await msg.reply_text("\n".join(lines))


@log_command
@require_admin
@feature_toggle("filters")
async def filteraction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if len(context.args) < 2:
        await msg.reply_text("Usage: /filteraction <keyword> <reply|delete|warn>")
        return
    keyword = context.args[0].strip().lower()
    action = context.args[1].strip().lower()
    if action not in {"reply", "delete", "warn"}:
        await msg.reply_text("Action must be reply, delete, or warn.")
        return
    db = context.application.bot_data["db"]
    await db.execute(
        "UPDATE chat_filters SET action = ? WHERE group_id = ? AND keyword = ?",
        (action, chat.id, keyword),
    )
    await msg.reply_text(f"Filter '{keyword}' action set to {action}.")


@feature_toggle("filters")
async def handle_message_filters(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None or not msg.text:
        return
    db = context.application.bot_data["db"]
    rows = await db.fetchall(
        "SELECT keyword, reply_text, action FROM chat_filters WHERE group_id = ?",
        (chat.id,),
    )
    text_lower = msg.text.lower()
    for row in rows:
        keyword = str(row["keyword"])
        if keyword not in text_lower:
            continue
        action = str(row["action"])
        if action == "delete":
            try:
                await msg.delete()
            except Exception:
                pass
            return
        if action == "warn":
            await msg.reply_text(
                f"{user.mention_html()} warned for filter: {keyword}", parse_mode="HTML"
            )
            return
        await msg.reply_text(str(row["reply_text"]))
        return


def register(application) -> None:
    application.add_handler(CommandHandler("filter", filter_cmd))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("filters", filters_cmd))
    application.add_handler(CommandHandler("filteraction", filteraction))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_filters),
        group=50,
    )

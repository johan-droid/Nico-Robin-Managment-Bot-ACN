from __future__ import annotations

import time
from typing import Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from core.decorators import feature_toggle, log_command, require_admin

MODULE_NAME = "welcome"


def _group_only(chat_type: str | None) -> bool:
    return chat_type in {"group", "supergroup"}


async def _get_settings(
    context: ContextTypes.DEFAULT_TYPE, group_id: int
) -> dict[str, Any]:
    cache = context.application.bot_data["cache"]
    db = context.application.bot_data["db"]
    key = f"welcome:settings:{group_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    row = await db.fetchone(
        "SELECT * FROM welcome_settings WHERE group_id = ?", (group_id,)
    )
    if row is None:
        row = {
            "group_id": group_id,
            "welcome_enabled": 1,
            "welcome_text": "Welcome {name} to {group}!",
            "farewell_enabled": 1,
            "farewell_text": "Farewell {name}.",
            "clean_welcome": 0,
        }
        await db.execute(
            """
            INSERT OR IGNORE INTO welcome_settings
                (group_id, welcome_enabled, welcome_text, farewell_enabled, farewell_text, clean_welcome)
            VALUES (?, 1, ?, 1, ?, 0)
            """,
            (group_id, row["welcome_text"], row["farewell_text"]),
        )
    cache.set(key, row, ttl=600)
    return row


async def _update_settings(
    context: ContextTypes.DEFAULT_TYPE, group_id: int, field: str, value: Any
) -> None:
    cache = context.application.bot_data["cache"]
    db = context.application.bot_data["db"]
    await db.execute(
        f"UPDATE welcome_settings SET {field} = ? WHERE group_id = ?", (value, group_id)
    )
    cache.delete(f"welcome:settings:{group_id}")


@log_command
@require_admin
@feature_toggle("welcome")
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    if not context.args:
        await msg.reply_text("Usage: /setwelcome <text>. Placeholders: {name}, {group}")
        return
    text = " ".join(context.args).strip()
    await _get_settings(context, chat.id)
    await _update_settings(context, chat.id, "welcome_text", text)
    await msg.reply_text("Welcome message updated.")


@log_command
@require_admin
@feature_toggle("welcome")
async def resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    await _get_settings(context, chat.id)
    await _update_settings(
        context, chat.id, "welcome_text", "Welcome {name} to {group}!"
    )
    await msg.reply_text("Welcome message reset.")


@log_command
@require_admin
@feature_toggle("welcome")
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    if not context.args or context.args[0].lower() not in {"on", "off"}:
        await msg.reply_text("Usage: /welcome on|off")
        return
    enabled = context.args[0].lower() == "on"
    await _get_settings(context, chat.id)
    await _update_settings(context, chat.id, "welcome_enabled", int(enabled))
    await msg.reply_text(f"Welcome messages {'enabled' if enabled else 'disabled'}.")


@log_command
@require_admin
@feature_toggle("welcome")
async def setfarewell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    if not context.args:
        await msg.reply_text(
            "Usage: /setfarewell <text>. Placeholders: {name}, {group}"
        )
        return
    text = " ".join(context.args).strip()
    await _get_settings(context, chat.id)
    await _update_settings(context, chat.id, "farewell_text", text)
    await msg.reply_text("Farewell message updated.")


@log_command
@require_admin
@feature_toggle("welcome")
async def farewell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    if not context.args or context.args[0].lower() not in {"on", "off"}:
        await msg.reply_text("Usage: /farewell on|off")
        return
    enabled = context.args[0].lower() == "on"
    await _get_settings(context, chat.id)
    await _update_settings(context, chat.id, "farewell_enabled", int(enabled))
    await msg.reply_text(f"Farewell messages {'enabled' if enabled else 'disabled'}.")


@log_command
@require_admin
@feature_toggle("welcome")
async def cleanwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    if not context.args or context.args[0].lower() not in {"on", "off"}:
        await msg.reply_text("Usage: /cleanwelcome on|off")
        return
    enabled = context.args[0].lower() == "on"
    await _get_settings(context, chat.id)
    await _update_settings(context, chat.id, "clean_welcome", int(enabled))
    await msg.reply_text(f"Clean welcome {'enabled' if enabled else 'disabled'}.")


@feature_toggle("welcome")
async def welcome_new_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    if not msg.new_chat_members:
        return

    settings = await _get_settings(context, chat.id)
    if not bool(settings["welcome_enabled"]):
        return

    cache = context.application.bot_data["cache"]
    for new_member in msg.new_chat_members:
        text = settings["welcome_text"].format(
            name=new_member.full_name, group=chat.title or "this group"
        )
        sent = await msg.reply_text(text)
        if bool(settings["clean_welcome"]):
            clean_key = f"welcome:last:{chat.id}"
            previous = cache.get(clean_key)
            if previous:
                try:
                    await context.bot.delete_message(chat.id, int(previous))
                except Exception:
                    pass
            cache.set(clean_key, sent.message_id, ttl=3600)

        db = context.application.bot_data["db"]
        await db.log_moderation(
            action_type="welcome_sent",
            moderator_id=0,
            target_id=new_member.id,
            group_id=chat.id,
            reason=None,
        )


@feature_toggle("welcome")
async def goodbye_left_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not _group_only(chat.type):
        return
    left_user = msg.left_chat_member
    if left_user is None:
        return
    settings = await _get_settings(context, chat.id)
    if not bool(settings["farewell_enabled"]):
        return
    text = settings["farewell_text"].format(
        name=left_user.full_name, group=chat.title or "this group"
    )
    await msg.reply_text(text)

    db = context.application.bot_data["db"]
    await db.log_moderation(
        action_type="farewell_sent",
        moderator_id=0,
        target_id=left_user.id,
        group_id=chat.id,
        reason=None,
    )


def register(application) -> None:
    application.add_handler(CommandHandler("setwelcome", setwelcome))
    application.add_handler(CommandHandler("resetwelcome", resetwelcome))
    application.add_handler(CommandHandler("welcome", welcome))
    application.add_handler(CommandHandler("setfarewell", setfarewell))
    application.add_handler(CommandHandler("farewell", farewell))
    application.add_handler(CommandHandler("cleanwelcome", cleanwelcome))
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members)
    )
    application.add_handler(
        MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_left_members)
    )

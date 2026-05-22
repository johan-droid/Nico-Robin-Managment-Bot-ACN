from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command

MODULE_NAME = "welcome"


async def _get_settings(context: ContextTypes.DEFAULT_TYPE, group_id: int) -> dict[str, object]:
    db = get_runtime(context)["db"]
    row = await db.fetchone(
        """
        SELECT welcome_text, farewell_text, rules_text, welcome_enabled, farewell_enabled, clean_welcome
        FROM group_settings WHERE group_id = ?
        """,
        (group_id,),
    )
    if row is None:
        return {
            "welcome_text": None,
            "farewell_text": None,
            "rules_text": None,
            "welcome_enabled": True,
            "farewell_enabled": True,
            "clean_welcome": False,
        }
    return {
        "welcome_text": row[0],
        "farewell_text": row[1],
        "rules_text": row[2],
        "welcome_enabled": bool(row[3]),
        "farewell_enabled": bool(row[4]),
        "clean_welcome": bool(row[5]),
    }


async def _upsert_group_setting(context: ContextTypes.DEFAULT_TYPE, group_id: int, field: str, value) -> None:
    db = get_runtime(context)["db"]
    settings = await _get_settings(context, group_id)
    settings[field] = value
    await db.execute(
        """
        INSERT INTO group_settings (group_id, welcome_text, farewell_text, rules_text, welcome_enabled, farewell_enabled, clean_welcome, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(group_id) DO UPDATE SET
            welcome_text = excluded.welcome_text,
            farewell_text = excluded.farewell_text,
            rules_text = excluded.rules_text,
            welcome_enabled = excluded.welcome_enabled,
            farewell_enabled = excluded.farewell_enabled,
            clean_welcome = excluded.clean_welcome,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            group_id,
            settings["welcome_text"],
            settings["farewell_text"],
            settings["rules_text"],
            1 if settings["welcome_enabled"] else 0,
            1 if settings["farewell_enabled"] else 0,
            1 if settings["clean_welcome"] else 0,
        ),
    )


@feature_toggle("welcome")
@log_command
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /setwelcome <message>")
        return
    await _upsert_group_setting(context, chat.id, "welcome_text", " ".join(args))
    await message.reply_text("🌸 Welcome message updated.")


@feature_toggle("welcome")
@log_command
async def resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    db = get_runtime(context)["db"]
    await db.execute("UPDATE group_settings SET welcome_text = NULL, updated_at = CURRENT_TIMESTAMP WHERE group_id = ?", (chat.id,))
    await message.reply_text("🌸 Welcome message cleared.")


@feature_toggle("welcome")
@log_command
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /welcome on|off")
        return
    enabled = args[0].lower() == "on"
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO group_settings (group_id, welcome_enabled, farewell_enabled, clean_welcome, updated_at)
        VALUES (?, ?, COALESCE((SELECT farewell_enabled FROM group_settings WHERE group_id = ?), 1), COALESCE((SELECT clean_welcome FROM group_settings WHERE group_id = ?), 0), CURRENT_TIMESTAMP)
        ON CONFLICT(group_id) DO UPDATE SET welcome_enabled = excluded.welcome_enabled, updated_at = CURRENT_TIMESTAMP
        """,
        (chat.id, 1 if enabled else 0, chat.id, chat.id),
    )
    await message.reply_text(f"🌸 Welcome messages {'enabled' if enabled else 'disabled'}.")


@feature_toggle("welcome")
@log_command
async def setfarewell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /setfarewell <message>")
        return
    await _upsert_group_setting(context, chat.id, "farewell_text", " ".join(args))
    await message.reply_text("🌸 Farewell message updated.")


@feature_toggle("welcome")
@log_command
async def farewell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /farewell on|off")
        return
    enabled = args[0].lower() == "on"
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO group_settings (group_id, welcome_enabled, farewell_enabled, clean_welcome, updated_at)
        VALUES (?, COALESCE((SELECT welcome_enabled FROM group_settings WHERE group_id = ?), 1), ?, COALESCE((SELECT clean_welcome FROM group_settings WHERE group_id = ?), 0), CURRENT_TIMESTAMP)
        ON CONFLICT(group_id) DO UPDATE SET farewell_enabled = excluded.farewell_enabled, updated_at = CURRENT_TIMESTAMP
        """,
        (chat.id, chat.id, 1 if enabled else 0, chat.id),
    )
    await message.reply_text(f"🌸 Farewell messages {'enabled' if enabled else 'disabled'}.")


@feature_toggle("welcome")
@log_command
async def cleanwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /cleanwelcome on|off")
        return
    enabled = args[0].lower() == "on"
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO group_settings (group_id, welcome_enabled, farewell_enabled, clean_welcome, updated_at)
        VALUES (?, COALESCE((SELECT welcome_enabled FROM group_settings WHERE group_id = ?), 1), COALESCE((SELECT farewell_enabled FROM group_settings WHERE group_id = ?), 1), ?, CURRENT_TIMESTAMP)
        ON CONFLICT(group_id) DO UPDATE SET clean_welcome = excluded.clean_welcome, updated_at = CURRENT_TIMESTAMP
        """,
        (chat.id, chat.id, chat.id, 1 if enabled else 0),
    )
    await message.reply_text(f"🌸 Clean welcome {'enabled' if enabled else 'disabled'}.")


@feature_toggle("welcome")
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None or not message.new_chat_members:
        return
    settings = await _get_settings(context, chat.id)
    if not settings["welcome_enabled"]:
        return
    text = settings["welcome_text"] or "🌸 Welcome to the group, {name}!"
    for new_member in message.new_chat_members:
        await message.reply_text(text.format(name=new_member.full_name))


@feature_toggle("welcome")
async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None or message.left_chat_member is None:
        return
    settings = await _get_settings(context, chat.id)
    if not settings["farewell_enabled"]:
        return
    text = settings["farewell_text"] or "🌸 Farewell, {name}."
    await message.reply_text(text.format(name=message.left_chat_member.full_name))


def register(application) -> None:
    application.add_handler(CommandHandler("setwelcome", setwelcome, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("resetwelcome", resetwelcome, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("welcome", welcome, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("setfarewell", setfarewell, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("farewell", farewell, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("cleanwelcome", cleanwelcome, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(MessageHandler(tg_filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(tg_filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))

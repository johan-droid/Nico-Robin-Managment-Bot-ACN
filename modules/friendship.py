from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command

MODULE_NAME = "friendship"


async def _ensure_state(context: ContextTypes.DEFAULT_TYPE, user_id: int, group_id: int) -> None:
    db = get_runtime(context)["db"]
    row = await db.fetchone("SELECT 1 FROM friendship_state WHERE user_id = ? AND group_id = ?", (user_id, group_id))
    if row is None:
        await db.execute("INSERT INTO friendship_state (user_id, group_id, bond_points, level, last_interaction_at) VALUES (?, ?, 0, 1, 0)", (user_id, group_id))


@feature_toggle("friendship")
@log_command
async def bond_with_yamato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None:
        return
    await _ensure_state(context, user.id, chat.id)
    await message.reply_text("🌸 The bond with Yamato has begun.")


@feature_toggle("friendship")
@log_command
async def yamato_interact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None:
        return
    args = context.args or []
    interaction = args[0].lower() if args else "moment"
    await _ensure_state(context, user.id, chat.id)
    db = get_runtime(context)["db"]
    await db.execute(
        "UPDATE friendship_state SET bond_points = bond_points + 1, last_interaction_at = strftime('%s','now') WHERE user_id = ? AND group_id = ?",
        (user.id, chat.id),
    )
    await db.execute(
        "INSERT INTO friendship_events (user_id, group_id, event_type, payload) VALUES (?, ?, ?, ?)",
        (user.id, chat.id, interaction, interaction),
    )
    await message.reply_text(f"🌸 Yamato interaction recorded: {interaction}.")


def register(application) -> None:
    application.add_handler(CommandHandler("bond_with_yamato", bond_with_yamato, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("yamato_interact", yamato_interact, filters=tg_filters.ChatType.GROUPS))

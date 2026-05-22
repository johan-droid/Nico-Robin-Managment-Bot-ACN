from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import log_command, require_commander_or_captain

MODULE_NAME = "feature_mgmt"

KNOWN_FEATURES = [
    "moderation",
    "federation",
    "filters",
    "welcome",
    "notes",
    "acn",
    "flirt",
    "points",
    "broadcast",
    "friendship",
    "fun",
]


async def _set_feature(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    enabled: bool,
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /enable <feature> or /disable <feature>")
        return
    feature = context.args[0].strip().lower()
    if feature not in KNOWN_FEATURES:
        await msg.reply_text(f"Unknown feature '{feature}'. Use /features.")
        return

    db = context.application.bot_data["db"]
    cache = context.application.bot_data["cache"]
    await db.set_feature_enabled(chat.id, feature, enabled=enabled, changed_by=user.id)
    cache.delete(f"feature:{chat.id}:{feature}")
    await msg.reply_text(f"Feature '{feature}' {'enabled' if enabled else 'disabled'}.")


@log_command
@require_commander_or_captain
async def features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    db = context.application.bot_data["db"]
    rows = await db.fetchall(
        """
        SELECT feature_name, enabled
        FROM group_features
        WHERE group_id = ?
        """,
        (chat.id,),
    )
    configured = {row["feature_name"]: bool(row["enabled"]) for row in rows}
    lines = ["Feature status:"]
    for feature in KNOWN_FEATURES:
        state = configured.get(feature, True)
        lines.append(f"- {feature}: {'ON' if state else 'OFF'}")
    await msg.reply_text("\n".join(lines))


@log_command
@require_commander_or_captain
async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_feature(update, context, enabled=True)


@log_command
@require_commander_or_captain
async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_feature(update, context, enabled=False)


@log_command
@require_commander_or_captain
async def toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /toggle <feature>")
        return
    feature = context.args[0].strip().lower()
    if feature not in KNOWN_FEATURES:
        await msg.reply_text(f"Unknown feature '{feature}'.")
        return
    db = context.application.bot_data["db"]
    cache = context.application.bot_data["cache"]
    current = await db.get_feature_enabled(chat.id, feature)
    await db.set_feature_enabled(
        chat.id, feature, enabled=not current, changed_by=update.effective_user.id
    )
    cache.delete(f"feature:{chat.id}:{feature}")
    await msg.reply_text(
        f"Feature '{feature}' {'enabled' if not current else 'disabled'}."
    )


def register(application) -> None:
    application.add_handler(CommandHandler("features", features))
    application.add_handler(CommandHandler("enable", enable))
    application.add_handler(CommandHandler("disable", disable))
    application.add_handler(CommandHandler("toggle", toggle))

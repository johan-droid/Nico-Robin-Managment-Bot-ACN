from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.cache import cache
from core.decorators import get_runtime, log_command, require_commander_or_captain

MODULE_NAME = "feature_mgmt"
AVAILABLE_FEATURES = (
    "moderation",
    "filters",
    "welcome",
    "notes",
    "acn",
    "flirt",
    "points",
    "broadcast",
    "friendship",
    "fun",
)


async def _set_feature_state(context: ContextTypes.DEFAULT_TYPE, group_id: int, feature_name: str, enabled: bool, changed_by: int | None) -> None:
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO group_features (group_id, feature_name, enabled, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(group_id, feature_name) DO UPDATE SET
            enabled = excluded.enabled,
            updated_at = CURRENT_TIMESTAMP
        """,
        (group_id, feature_name, 1 if enabled else 0),
    )
    await db.execute(
        """
        INSERT INTO feature_logs (feature_name, group_id, action, changed_by)
        VALUES (?, ?, ?, ?)
        """,
        (feature_name, group_id, "enable" if enabled else "disable", changed_by),
    )
    cache.delete(f"feature:{group_id}:{feature_name}")


@log_command
async def features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    db = get_runtime(context)["db"]
    rows = await db.fetchall(
        "SELECT feature_name, enabled FROM group_features WHERE group_id = ? ORDER BY feature_name",
        (chat.id,),
    )
    enabled_map = {row[0]: bool(row[1]) for row in rows}
    lines = ["🌸 Feature status:"]
    for feature_name in AVAILABLE_FEATURES:
        state = "enabled" if enabled_map.get(feature_name, True) else "disabled"
        lines.append(f"• {feature_name}: {state}")
    await message.reply_text("\n".join(lines))


@require_commander_or_captain
@log_command
async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle_feature(update, context, True)


@require_commander_or_captain
@log_command
async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle_feature(update, context, False)


@require_commander_or_captain
@log_command
async def toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /toggle <feature>")
        return

    feature_name = args[0].lower().strip()
    db = get_runtime(context)["db"]
    row = await db.fetchone(
        "SELECT enabled FROM group_features WHERE group_id = ? AND feature_name = ?",
        (chat.id, feature_name),
    )
    enabled = True if row is None else not bool(row[0])
    await _set_feature_state(context, chat.id, feature_name, enabled, update.effective_user.id if update.effective_user else None)
    await message.reply_text(f"🌸 {feature_name} is now {'enabled' if enabled else 'disabled'}.")


async def _toggle_feature(update: Update, context: ContextTypes.DEFAULT_TYPE, enabled: bool) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /enable <feature>" if enabled else "🌸 Usage: /disable <feature>")
        return

    feature_name = args[0].lower().strip()
    await _set_feature_state(context, chat.id, feature_name, enabled, update.effective_user.id if update.effective_user else None)
    await message.reply_text(f"🌸 {feature_name} is now {'enabled' if enabled else 'disabled'}.")


def register(application) -> None:
    application.add_handler(CommandHandler("features", features, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("enable", enable, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("disable", disable, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("toggle", toggle, filters=tg_filters.ChatType.GROUPS))

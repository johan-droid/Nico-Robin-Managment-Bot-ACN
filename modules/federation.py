from __future__ import annotations

import time
from typing import Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command, require_admin

MODULE_NAME = "federation"


def _parse_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id
    if context.args and context.args[0].lstrip("-").isdigit():
        return int(context.args[0])
    return None


@log_command
@require_admin
@feature_toggle("federation")
async def fban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    if chat is None or user is None or msg is None:
        return
    target_id = _parse_target(update, context)
    if target_id is None:
        await msg.reply_text("Usage: /fban <user_id> [reason] or reply + /fban")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "federation ban"
    # Rose-style pattern: publish one event; ban fanout is handled asynchronously.
    await context.application.bot_data["event_bus"].publish(
        "fed_ban:new",
        {
            "fed_id": str(chat.id),
            "group_id": chat.id,
            "target_id": target_id,
            "moderator_id": user.id,
            "reason": reason,
        },
    )
    await msg.reply_text(f"Federation ban queued for {target_id}.")


async def _on_fed_ban(event: dict[str, Any]) -> None:
    app = event["data"]["application"]
    payload = event["data"]["payload"]
    db = app.bot_data["db"]
    bot = app.bot
    fed_id = str(payload["fed_id"])
    target_id = int(payload["target_id"])
    moderator_id = int(payload["moderator_id"])
    reason = str(payload.get("reason", "federation ban"))

    await db.execute(
        """
        INSERT INTO federation_bans (fed_id, user_id, banned_by, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (fed_id, target_id, moderator_id, reason, int(time.time())),
    )

    groups = await db.fetchall(
        "SELECT group_id FROM federation_groups WHERE fed_id = ?",
        (fed_id,),
    )
    for row in groups:
        group_id = int(row["group_id"])
        try:
            await bot.ban_chat_member(group_id, target_id)
        except Exception:
            continue


def _listener_bridge(application):
    async def callback(event: dict[str, Any]) -> None:
        wrapped = {
            "event_type": event["event_type"],
            "data": {
                "application": application,
                "payload": event["data"],
            },
        }
        await _on_fed_ban(wrapped)

    return callback


def register(application) -> None:
    application.add_handler(CommandHandler("fban", fban))
    application.bot_data["event_bus"].subscribe(
        "fed_ban:new",
        _listener_bridge(application),
        name="federation.fban.listener",
    )

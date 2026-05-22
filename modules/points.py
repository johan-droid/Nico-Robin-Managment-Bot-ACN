from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command, require_acn_member

MODULE_NAME = "points"


def _level_for_points(points: int) -> int:
    level = 1
    while points >= (level * 100):
        level += 1
    return level


async def _ensure_user_row(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    db = context.application.bot_data["db"]
    row = await db.fetchone(
        "SELECT user_id FROM user_points WHERE user_id = ?", (user_id,)
    )
    if row is None:
        await db.execute(
            "INSERT INTO user_points (user_id, points, level, last_message_time) VALUES (?, 0, 1, 0)",
            (user_id,),
        )


async def _on_points_add(event: dict[str, Any]) -> None:
    app = event["data"]["application"]
    db = app.bot_data["db"]
    cache = app.bot_data["cache"]
    payload = event["data"]["payload"]
    user_id = int(payload["user_id"])
    points_delta = int(payload["points"])
    reason = str(payload.get("reason", "event"))

    row = await db.fetchone(
        "SELECT points FROM user_points WHERE user_id = ?", (user_id,)
    )
    current = int(row["points"]) if row else 0
    new_points = max(0, current + points_delta)
    level = _level_for_points(new_points)

    if row is None:
        await db.execute(
            "INSERT INTO user_points (user_id, points, level, last_message_time) VALUES (?, ?, ?, ?)",
            (user_id, new_points, level, int(time.time())),
        )
    else:
        await db.execute(
            "UPDATE user_points SET points = ?, level = ?, last_message_time = ? WHERE user_id = ?",
            (new_points, level, int(time.time()), user_id),
        )

    await db.execute(
        "INSERT INTO point_transactions (user_id, points, reason, created_at) VALUES (?, ?, ?, ?)",
        (user_id, points_delta, reason, int(time.time())),
    )
    cache.set(f"points:{user_id}", {"points": new_points, "level": level}, ttl=300)


def _event_bridge(application) -> Callable[[dict[str, Any]], Awaitable[None]]:
    async def callback(event: dict[str, Any]) -> None:
        wrapped = {
            "event_type": event["event_type"],
            "data": {
                "application": application,
                "payload": event["data"],
            },
        }
        await _on_points_add(wrapped)

    return callback


@log_command
@require_acn_member
@feature_toggle("points")
async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    db = context.application.bot_data["db"]
    cache = context.application.bot_data["cache"]
    key = f"points:{user.id}"
    cached = cache.get(key)
    if cached is None:
        await _ensure_user_row(context, user.id)
        row = await db.fetchone(
            "SELECT points, level FROM user_points WHERE user_id = ?", (user.id,)
        )
        cached = {"points": int(row["points"]), "level": int(row["level"])}
        cache.set(key, cached, ttl=300)
    await msg.reply_text(f"Points: {cached['points']}\nLevel: {cached['level']}")


@log_command
@require_acn_member
@feature_toggle("points")
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    db = context.application.bot_data["db"]
    rows = await db.fetchall(
        "SELECT user_id, points, level FROM user_points ORDER BY points DESC LIMIT 10"
    )
    if not rows:
        await msg.reply_text("No leaderboard data yet.")
        return
    lines = ["Top Points"]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"{idx}. {row['user_id']} - {row['points']} pts (Lv {row['level']})"
        )
    await msg.reply_text("\n".join(lines))


def register(application) -> None:
    application.add_handler(CommandHandler("points", points))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    event_bus = application.bot_data["event_bus"]
    event_bus.subscribe(
        "points:add", _event_bridge(application), name="points.add.listener"
    )

from __future__ import annotations

import asyncio
from collections import defaultdict
from types import SimpleNamespace
from time import time
from uuid import uuid4

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command

MODULE_NAME = "points"
POINT_LOCKS: dict[tuple[int, int], asyncio.Lock] = defaultdict(asyncio.Lock)


async def _recalc_level(total_points: int) -> int:
    if total_points < 100:
        return 1
    if total_points < 250:
        return 2
    if total_points < 500:
        return 3
    if total_points < 1000:
        return 4
    if total_points < 2000:
        return 5
    if total_points < 5000:
        return 6
    if total_points < 10000:
        return 7
    if total_points < 25000:
        return 8
    if total_points < 50000:
        return 9
    return 10


async def _award_points(context: ContextTypes.DEFAULT_TYPE, user_id: int, group_id: int, points: int, reason: str, cooldown: int = 0, transaction_uid: str | None = None) -> bool:
    lock = POINT_LOCKS[(group_id, user_id)]
    async with lock:
        db = get_runtime(context)["db"]
        row = await db.fetchone("SELECT points, last_message_time FROM user_points WHERE user_id = ?", (user_id,))
        if row is None:
            await db.execute("INSERT INTO user_points (user_id, points, level, last_message_time) VALUES (?, 0, 1, 0)", (user_id,))
            row = (0, 0)
        current_points = int(row[0])
        last_message_time = int(row[1]) if len(row) > 1 else 0
        now = int(time())
        if cooldown and now - last_message_time < cooldown:
            return False
        if not transaction_uid:
            transaction_uid = str(uuid4())
        duplicate = await db.fetchone("SELECT 1 FROM point_transactions WHERE transaction_uid = ?", (transaction_uid,))
        if duplicate:
            return False
        new_points = current_points + points
        new_level = await _recalc_level(new_points)
        await db.execute("UPDATE user_points SET points = ?, level = ?, last_message_time = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (new_points, new_level, now, user_id))
        await db.execute(
            "INSERT INTO point_transactions (user_id, points, reason, transaction_uid) VALUES (?, ?, ?, ?)",
            (user_id, points, reason, transaction_uid),
        )
        return True


async def handle_points_add(payload: dict) -> None:
    await _award_points(
        payload["context"],
        payload["user_id"],
        payload["group_id"],
        int(payload["points"]),
        payload.get("reason", "event"),
        int(payload.get("cooldown", 0)),
        payload.get("transaction_uid"),
    )


@feature_toggle("points")
@log_command
async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    row = await get_runtime(context)["db"].fetchone("SELECT points, level FROM user_points WHERE user_id = ?", (user.id,))
    points_value = int(row[0]) if row else 0
    level = int(row[1]) if row else 1
    await message.reply_text(f"🌸 {user.full_name}: {points_value} points, level {level}")


@feature_toggle("points")
@log_command
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    rows = await get_runtime(context)["db"].fetchall("SELECT user_id, points, level FROM user_points ORDER BY points DESC LIMIT 10")
    if not rows:
        await message.reply_text("🌸 No points yet.")
        return
    lines = ["🌸 Leaderboard:"]
    for index, row in enumerate(rows, 1):
        lines.append(f"{index}. {row[0]} - {row[1]} points (Lv {row[2]})")
    await message.reply_text("\n".join(lines))


async def points_add_listener(payload: dict) -> None:
    context = payload.get("context")
    if context is None:
        return
    await _award_points(
        context,
        int(payload["user_id"]),
        int(payload["group_id"]),
        int(payload["points"]),
        payload.get("reason", "unknown"),
        int(payload.get("cooldown", 0)),
        payload.get("transaction_uid", str(uuid4())),
    )


@log_command
async def award_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("🌸 Points are event-driven. Use /award from ACN or flirt success events.")


def register(application) -> None:
    bus = application.bot_data["event_bus"]

    async def _points_add_adapter(payload: dict) -> None:
        await points_add_listener({**payload, "context": SimpleNamespace(application=application)})

    bus.subscribe("points:add", _points_add_adapter)
    application.add_handler(CommandHandler("points", points, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("leaderboard", leaderboard, filters=tg_filters.ChatType.GROUPS))

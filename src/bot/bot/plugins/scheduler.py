from __future__ import annotations

from datetime import UTC, datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.tasks.announce_tasks import schedule_announcement
from src.bot.utils.decorators import admin_only, group_only
from src.bot.utils.time import parse_duration, until_datetime


def _parse_run_at(raw: str) -> datetime | None:
    if raw.startswith("+"):
        return until_datetime(parse_duration(raw.removeprefix("+")))
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@group_only
@admin_only
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    args = context.args or []
    if msg is None or chat is None or len(args) < 2:
        if msg:
            await msg.reply_text("🌸 Usage: /schedule +2h The announcement text")
        return
    run_at = _parse_run_at(args[0])
    text = " ".join(args[1:]).strip()
    if run_at is None or not text:
        await msg.reply_text("🌸 I could not read that time inscription.")
        return
    task_id = schedule_announcement(chat.id, text, run_at)
    await msg.reply_text(f"🌸 Announcement scheduled. Archive task: {task_id}")


def register(app) -> None:
    pass

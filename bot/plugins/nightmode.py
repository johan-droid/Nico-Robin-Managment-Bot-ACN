from __future__ import annotations

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database import async_session_factory
from models.group import Group
from utils.decorators import admin_only, group_only

logger = structlog.get_logger(__name__)


@group_only
@admin_only
async def nightmode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    args = context.args or []

    if msg is None or chat is None:
        return

    if not args or args[0].lower() not in ("on", "off"):
        await msg.reply_text("🌸 Usage: /nightmode [on|off]")
        return

    enable = args[0].lower() == "on"

    async with async_session_factory() as session:
        result = await session.execute(select(Group).where(Group.group_id == chat.id))
        group = result.scalar_one_or_none()

        if not group:
            await msg.reply_text("🌸 Group not found in database.")
            return

        group.nightmode_enabled = enable
        await session.commit()

    status = "enabled" if enable else "disabled"
    await msg.reply_text(f"🌸 Nightmode has been {status} for this group.")


def register(app) -> None:
    app.add_handler(CommandHandler("nightmode", nightmode))

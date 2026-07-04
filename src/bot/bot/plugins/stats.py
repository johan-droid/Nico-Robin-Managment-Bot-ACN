from __future__ import annotations

from sqlalchemy import func, select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.database import async_session_factory
from src.bot.models.user import GroupMember
from src.bot.models.warn import Warn
from src.bot.utils.decorators import group_only


@group_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    async with async_session_factory() as session:
        member_count = (
            await session.execute(
                select(func.count(GroupMember.user_id)).where(
                    GroupMember.group_id == chat.id
                )
            )
        ).scalar_one()
        warn_count = (
            await session.execute(
                select(func.count(Warn.warn_id)).where(
                    Warn.group_id == chat.id,
                    Warn.is_active.is_(True),
                )
            )
        ).scalar_one()
    await msg.reply_text(
        "🌸 Group archive\n"
        f"Members tracked: {member_count}\n"
        f"Active warnings: {warn_count}"
    )


def register(app) -> None:
    pass

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.database import async_session_factory
from src.bot.services.group_service import GroupService
from src.bot.utils.decorators import admin_only, group_only


def _state_arg(args: list[str]) -> bool | None:
    if not args:
        return None
    raw = args[0].lower()
    if raw in {"on", "enable", "enabled", "true"}:
        return True
    if raw in {"off", "disable", "disabled", "false"}:
        return False
    return None


@group_only
@admin_only
async def captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    state = _state_arg(context.args or [])
    if state is None:
        await msg.reply_text("🌸 Choose on or off for CAPTCHA.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, captcha_enabled=state)
    await msg.reply_text(f"🌸 CAPTCHA is now {'on' if state else 'off'}.")


def register(app) -> None:
    pass

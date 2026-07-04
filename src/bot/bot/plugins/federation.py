from __future__ import annotations

import uuid

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.database import async_session_factory
from src.bot.services.federation_service import FederationService
from src.bot.services.group_service import GroupService
from src.bot.services.user_service import UserService
from src.bot.utils.decorators import admin_only, group_only, owner_only


@group_only
@owner_only
async def newfed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    name = " ".join(context.args or []).strip()
    if not name:
        await msg.reply_text("🌸 Give this federation a name.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await UserService.ensure_user(session, user)
            federation = await FederationService.create_federation(
                session, name, user.id
            )
    await msg.reply_text(f"🌸 Federation created: {federation.fed_id}")


@group_only
@admin_only
async def joinfed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not context.args:
        return
    try:
        fed_id = uuid.UUID(context.args[0])
    except ValueError:
        await msg.reply_text("🚫 Invalid federation ID. Please provide a valid UUID.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await FederationService.join_group(session, fed_id, chat.id)
    await msg.reply_text("🌸 This group has joined the federation archive.")


def register(app) -> None:
    pass

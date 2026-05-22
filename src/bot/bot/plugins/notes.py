from __future__ import annotations

from telegram import Update
from telegram.ext import (
    ContextTypes,
    MessageHandler,
)
from telegram.ext import (
    filters as tg_filters,
)

from src.bot.database import async_session_factory
from src.bot.services.group_service import GroupService
from src.bot.services.note_service import NoteService
from src.bot.services.user_service import UserService
from src.bot.utils.decorators import admin_only, group_only
from src.bot.utils.i18n import gettext


@group_only
@admin_only
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not context.args:
        if msg:
            await msg.reply_text("🌸 Usage: /save name content")
        return
    name = context.args[0]
    content = " ".join(context.args[1:]).strip()
    if not content and msg.reply_to_message:
        content = (
            msg.reply_to_message.text_html or msg.reply_to_message.caption_html or ""
        )
    if not content:
        await msg.reply_text("🌸 Give me a note to archive.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            if update.effective_user:
                await UserService.ensure_user(session, update.effective_user)
            try:
                await NoteService.save_note(
                    session,
                    chat.id,
                    name,
                    content,
                    update.effective_user.id if update.effective_user else None,
                )
            except ValueError:
                await msg.reply_text(
                    "🌸 Note names may use only letters, numbers, and underscores, up to 32 characters."
                )
                return
    await msg.reply_text(gettext("note.saved"))


@group_only
async def get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not context.args:
        return
    async with async_session_factory() as session:
        try:
            note = await NoteService.get_note(session, chat.id, context.args[0])
        except ValueError:
            await msg.reply_text(
                "🌸 That note name does not belong in my archive. Use letters, numbers, or underscores only."
            )
            return
    if note is None:
        await msg.reply_text("🌸 I do not have that page in the archive.")
        return
    await msg.reply_text(note.content)


@group_only
async def hashtag_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not msg.text:
        return
    name = msg.text.split()[0].removeprefix("#")
    async with async_session_factory() as session:
        try:
            note = await NoteService.get_note(session, chat.id, name)
        except ValueError:
            return
    if note:
        await msg.reply_text(note.content)


@group_only
async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    async with async_session_factory() as session:
        items = await NoteService.list_notes(session, chat.id)
    if not items:
        await msg.reply_text("🌸 No notes are archived for this group.")
        return
    await msg.reply_text("🌸 Notes:\n" + "\n".join(f"- {item.name}" for item in items))


@group_only
@admin_only
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not context.args:
        return
    async with async_session_factory() as session:
        async with session.begin():
            try:
                removed = await NoteService.delete_note(
                    session, chat.id, context.args[0]
                )
            except ValueError:
                await msg.reply_text(
                    "🌸 That note name is malformed. Keep it to letters, numbers, and underscores."
                )
                return
    await msg.reply_text(
        "🌸 Note cleared." if removed else "🌸 That note was not archived."
    )


def register(app) -> None:
    app.add_handler(
        MessageHandler(tg_filters.Regex(r"^#[A-Za-z0-9_]+"), hashtag_note), group=25
    )

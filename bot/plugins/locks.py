from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
)
from telegram.ext import (
    filters as tg_filters,
)

from database import async_session_factory
from services.group_service import GroupService
from utils.decorators import admin_only, group_only
from utils.permissions import is_telegram_admin

logger = structlog.get_logger(__name__)

SUPPORTED_LOCK_TYPES = {
    "audio",
    "voice",
    "contact",
    "document",
    "photo",
    "sticker",
    "video",
    "forward",
    "link",
}


@group_only
@admin_only
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat:
        return

    if not context.args:
        await msg.reply_text(
            "🌸 Please provide a media type to lock. Example: `/lock photo`"
        )
        return

    lock_type = context.args[0].lower()
    if lock_type not in SUPPORTED_LOCK_TYPES:
        await msg.reply_text(
            f"🌸 Unsupported type. Supported types: {', '.join(SUPPORTED_LOCK_TYPES)}"
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)

            # Create a copy to update
            current_locks = dict(group.locked_media) if group.locked_media else {}
            if current_locks.get(lock_type):
                await msg.reply_text(f"🌸 `{lock_type}` is already locked.")
                return

            current_locks[lock_type] = True
            await GroupService.update_settings(
                session, chat.id, locked_media=current_locks
            )

    await msg.reply_text(f"🌸 Locked `{lock_type}` in this group.")


@group_only
@admin_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat:
        return

    if not context.args:
        await msg.reply_text(
            "🌸 Please provide a media type to unlock. Example: `/unlock photo`"
        )
        return

    lock_type = context.args[0].lower()
    if lock_type not in SUPPORTED_LOCK_TYPES:
        await msg.reply_text(
            f"🌸 Unsupported type. Supported types: {', '.join(SUPPORTED_LOCK_TYPES)}"
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)

            current_locks = dict(group.locked_media) if group.locked_media else {}
            if not current_locks.get(lock_type):
                await msg.reply_text(f"🌸 `{lock_type}` is not currently locked.")
                return

            current_locks[lock_type] = False
            await GroupService.update_settings(
                session, chat.id, locked_media=current_locks
            )

    await msg.reply_text(f"🌸 Unlocked `{lock_type}` in this group.")


@group_only
@admin_only
async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat:
        return

    async with async_session_factory() as session:
        group = await GroupService.get_group(session, chat.id)

    current_locks = group.locked_media if group and group.locked_media else {}
    locked_types = [k for k, v in current_locks.items() if v]

    if not locked_types:
        await msg.reply_text("🌸 There are no active locks in this group.")
        return

    await msg.reply_text(
        "🌸 Current locked media types:\n- " + "\n- ".join(locked_types)
    )


async def check_locked_media(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not msg or not chat or not user:
        return

    # Check if user is admin (exempt)
    is_admin = await is_telegram_admin(context, chat.id, user.id)
    if is_admin:
        return

    async with async_session_factory() as session:
        group = await GroupService.get_group(session, chat.id)

    if not group or not group.locked_media:
        return

    locks = group.locked_media
    deleted = False

    if locks.get("audio") and msg.audio:
        deleted = True
    elif locks.get("voice") and msg.voice:
        deleted = True
    elif locks.get("contact") and msg.contact:
        deleted = True
    elif locks.get("document") and msg.document:
        deleted = True
    elif locks.get("photo") and msg.photo:
        deleted = True
    elif locks.get("sticker") and msg.sticker:
        deleted = True
    elif locks.get("video") and msg.video:
        deleted = True
    elif locks.get("forward") and msg.forward_origin:
        deleted = True
    elif locks.get("link"):
        # Check for URLs in entities
        entities = msg.parse_entities(["url", "text_link"])
        if entities:
            deleted = True

    if deleted:
        try:
            await msg.delete()
            # Optionally send a warning message and delete it after a delay
            # warning = await msg.reply_text("🌸 This media type is locked in this group.")
            # ... delete warning after X seconds ...
        except Exception as e:
            logger.warning(f"Failed to delete locked media in {chat.id}: {e}")


def register(application: Application) -> None:
    application.add_handler(CommandHandler("lock", lock_cmd))
    application.add_handler(CommandHandler("unlock", unlock_cmd))
    application.add_handler(CommandHandler("locks", locks_cmd))

    # Run the message handler in group 1
    application.add_handler(
        MessageHandler(
            tg_filters.ChatType.GROUPS & ~tg_filters.Command(), check_locked_media
        ),
        group=1,
    )

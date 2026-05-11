from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
)
from telegram.ext import (
    filters as tg_filters,
)

from bot.middleware.flood_control import raid_threshold_reached
from bot.middleware.rate_limiter import get_redis
from config import settings
from database import async_session_factory
from services.audit_service import AuditService
from services.group_service import GroupService
from services.user_service import UserService
from utils.decorators import admin_only, group_only
from utils.formatters import format_welcome
from utils.i18n import gettext

LAST_WELCOME_KEY = "welcome:last:{chat_id}"


def _state_arg(args: list[str]) -> bool | None:
    if not args:
        return None
    raw = args[0].lower()
    if raw in {"on", "yes", "true", "enable", "enabled"}:
        return True
    if raw in {"off", "no", "false", "disable", "disabled"}:
        return False
    return None


async def _member_count(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> int | None:
    try:
        return await context.bot.get_chat_member_count(chat_id)
    except Exception:
        return None


async def welcome_new_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or not msg.new_chat_members:
        return
    async with async_session_factory() as session:
        async with session.begin():
            group = await GroupService.ensure_group(session, chat)
            for member in msg.new_chat_members:
                await UserService.ensure_user(session, member)
            if group.antiraid_enabled and await raid_threshold_reached(chat.id):
                await AuditService.log_action(
                    session,
                    group_id=chat.id,
                    action="raid_detected",
                    reason="Join threshold exceeded",
                )

    # ── Log new member to log channel ──
    log_channel_id = group.log_channel_id or settings.log_channel_id
    if log_channel_id:
        count = await _member_count(context, chat.id)
        for member in msg.new_chat_members:
            username_line = (
                f"📛 **Username:** @{member.username}\n" if member.username else ""
            )
            join_text = (
                f"👋 **New Member Joined**\n\n"
                f"👤 **Name:** {member.first_name or ''} {member.last_name or ''}\n"
                f"🆔 **User ID:** `{member.id}`\n"
                f"{username_line}"
                f"🤖 **Is Bot:** {'Yes' if member.is_bot else 'No'}\n"
                f"🏠 **Group:** {chat.title}\n"
                f"👥 **Members Now:** {count or '?'}\n"
                f"🕐 **Joined At:** {msg.date.strftime('%Y-%m-%d %H:%M UTC') if msg.date else 'N/A'}"
            )
            try:
                await context.bot.send_message(
                    chat_id=log_channel_id,
                    text=join_text,
                    parse_mode="Markdown",
                )
            except Exception:
                pass  # Log channel may be unreachable

    if not group.welcome_enabled:
        return
    redis = get_redis()
    key = LAST_WELCOME_KEY.format(chat_id=chat.id)
    if group.clean_welcome:
        previous = await redis.get(key)
        if previous:
            try:
                await context.bot.delete_message(chat.id, int(previous))
            except Exception:
                pass
    count = await _member_count(context, chat.id)
    for member in msg.new_chat_members:
        text = format_welcome(
            template=group.welcome_text,
            first=member.first_name,
            username=f"@{member.username}" if member.username else member.full_name,
            chat=chat.title or str(chat.id),
            count=count,
            locale=group.locale,
        )
        sent = await msg.reply_text(text)
        await redis.set(key, sent.message_id, ex=86400)


async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None or msg.left_chat_member is None:
        return
    async with async_session_factory() as session:
        group = await GroupService.get_group(session, chat.id)

    user = msg.left_chat_member

    # ── Log departure to log channel ──
    log_channel_id = None
    if group:
        log_channel_id = group.log_channel_id or settings.log_channel_id
    else:
        log_channel_id = settings.log_channel_id

    if log_channel_id:
        count = await _member_count(context, chat.id)
        leave_text = (
            f"🚪 **Member Left**\n\n"
            f"👤 **Name:** {user.first_name or ''} {user.last_name or ''}\n"
            f"🆔 **User ID:** `{user.id}`\n"
            f"📛 **Username:** {'@' + user.username if user.username else 'N/A'}\n"
            f"🤖 **Is Bot:** {'Yes' if user.is_bot else 'No'}\n"
            f"🏠 **Group:** {chat.title}\n"
            f"👥 **Members Now:** {count or '?'}\n"
            f"🕐 **Left At:** {msg.date.strftime('%Y-%m-%d %H:%M UTC') if msg.date else 'N/A'}"
        )
        try:
            await context.bot.send_message(
                chat_id=log_channel_id,
                text=leave_text,
                parse_mode="Markdown",
            )
        except Exception:
            pass  # Log channel may be unreachable

    if group is None or not group.farewell_enabled:
        return
    template = group.farewell_text or "🌸 {first} has left the archive."
    await msg.reply_text(
        template.format(
            first=user.first_name,
            username=f"@{user.username}" if user.username else user.full_name,
            chat=chat.title or str(chat.id),
            count="?",
        )
    )


@group_only
@admin_only
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    text = " ".join(context.args or []).strip()
    if not text and msg.reply_to_message:
        text = msg.reply_to_message.text_html or msg.reply_to_message.caption_html or ""
    if not text:
        await msg.reply_text("🌸 Give me a welcome text to archive.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, welcome_text=text)
    await msg.reply_text(gettext("welcome.saved"))


@group_only
@admin_only
async def resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, welcome_text=None)
    await msg.reply_text(gettext("welcome.reset"))


@group_only
@admin_only
async def welcome_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    state = _state_arg(context.args or [])
    if state is None:
        await msg.reply_text("🌸 Choose on or off.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, welcome_enabled=state)
    await msg.reply_text(gettext("welcome.enabled", state="on" if state else "off"))


@group_only
@admin_only
async def setfarewell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    text = " ".join(context.args or []).strip()
    if not text:
        await msg.reply_text("🌸 Give me a farewell text to archive.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, farewell_text=text)
    await msg.reply_text(gettext("farewell.saved"))


@group_only
@admin_only
async def farewell_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    state = _state_arg(context.args or [])
    if state is None:
        await msg.reply_text("🌸 Choose on or off.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, farewell_enabled=state)
    await msg.reply_text(f"🌸 Farewell messages are now {'on' if state else 'off'}.")


@group_only
@admin_only
async def cleanwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    state = _state_arg(context.args or [])
    if state is None:
        await msg.reply_text("🌸 Choose on or off.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, clean_welcome=state)
    await msg.reply_text(f"🌸 Clean welcome is now {'on' if state else 'off'}.")


@group_only
@admin_only
async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    text = " ".join(context.args or []).strip()
    if not text and msg.reply_to_message:
        text = msg.reply_to_message.text_html or msg.reply_to_message.caption_html or ""
    if not text:
        await msg.reply_text("🌸 Give me rules to archive.")
        return
    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await GroupService.update_settings(session, chat.id, rules=text)
    await msg.reply_text(gettext("rules.saved"))


@group_only
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    async with async_session_factory() as session:
        group = await GroupService.get_group(session, chat.id)
    if group is None or not group.rules:
        await msg.reply_text(gettext("rules.empty"))
        return
    await msg.reply_text(group.rules)


@group_only
async def welcometest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return
    async with async_session_factory() as session:
        group = await GroupService.get_group(session, chat.id)
    await msg.reply_text(
        format_welcome(
            template=group.welcome_text if group else None,
            first=user.first_name,
            username=f"@{user.username}" if user.username else user.full_name,
            chat=chat.title or str(chat.id),
            count=await _member_count(context, chat.id),
            locale=group.locale if group else "en",
        )
    )


def register(app) -> None:
    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("resetwelcome", resetwelcome))
    app.add_handler(CommandHandler("welcome", welcome_toggle))
    app.add_handler(CommandHandler("setfarewell", setfarewell))
    app.add_handler(CommandHandler("farewell", farewell_toggle))
    app.add_handler(CommandHandler("cleanwelcome", cleanwelcome))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("welcometest", welcometest))
    app.add_handler(
        MessageHandler(tg_filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members),
        group=5,
    )
    app.add_handler(
        MessageHandler(tg_filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member),
        group=5,
    )

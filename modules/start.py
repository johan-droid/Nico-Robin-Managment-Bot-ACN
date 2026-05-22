from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from core.cache import cache
from core.decorators import get_runtime, log_command

MODULE_NAME = "start"


def _bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    username = getattr(context.bot, "username", None)
    return username or "YourBot"


def _start_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    bot_username = _bot_username(context)
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 Help", callback_data="start:help")],
            [InlineKeyboardButton("⭐ About", callback_data="start:about")],
            [
                InlineKeyboardButton(
                    "👥 Add to Group",
                    url=f"https://t.me/{bot_username}?startgroup=start",
                )
            ],
        ]
    )


def _help_text() -> str:
    return (
        "🌸 Main help\n\n"
        "Use me in groups to manage moderation, welcome flows, notes, points, flirting, and ACN tools.\n\n"
        "Popular commands:\n"
        "• /features - view module status\n"
        "• /welcome - manage welcome messages\n"
        "• /points - check loyalty points\n"
        "• /flirt - try a flirt line\n"
        "• /help - show the help menu again"
    )


def _about_text() -> str:
    return (
        "🌸 About Nico Robin Bot\n\n"
        "I help keep Telegram groups clean, fun, and organized. I can moderate chats, welcome new members, track ACN loyalty, manage notes and filters, and power playful features like flirting and friendship systems."
    )


def _private_welcome_text(first_name: str, start_param: str | None) -> str:
    intro = (
        f"Hello {html.escape(first_name)}! 👋\n\n"
        "I'm Nico Robin, your smart Telegram group manager. I can:\n"
        "✅ Automatically block spam & bad content\n"
        "✅ Welcome new members\n"
        "✅ Track loyalty points (ACN crew)\n"
        "✅ Flirt, play, and more!\n\n"
        "Use the buttons below to get started."
    )

    if start_param == "invite":
        return intro + "\n\nThanks for joining through an invite link."
    return intro


async def _record_private_start(context: ContextTypes.DEFAULT_TYPE, user, start_param: str | None) -> None:
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO user_starts (user_id, username, first_name, start_param, start_count, first_started_at, last_started_at)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            start_param = excluded.start_param,
            start_count = user_starts.start_count + 1,
            last_started_at = CURRENT_TIMESTAMP
        """,
        (
            user.id,
            user.username,
            user.first_name,
            start_param,
        ),
    )


async def _group_rate_limited(chat_id: int, user_id: int) -> bool:
    cache_key = f"start:group:last:{chat_id}:{user_id}"
    if cache.get(cache_key):
        return True
    cache.set(cache_key, True, ttl=3600)
    return False


@log_command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return

    args = context.args or []
    start_param = args[0].lower().strip() if args else None

    if chat.type == "private":
        if start_param == "help":
            await message.reply_text(_help_text(), reply_markup=_start_keyboard(context))
        elif start_param == "about":
            await message.reply_text(_about_text(), reply_markup=_start_keyboard(context))
        else:
            await message.reply_text(
                _private_welcome_text(user.first_name or "there", start_param),
                reply_markup=_start_keyboard(context),
            )
        await _record_private_start(context, user, start_param)
        return

    if await _group_rate_limited(chat.id, user.id):
        return

    await message.reply_text(
        (
            f"{user.mention_html()}, thanks for starting me in this group! 😊\n\n"
            "I'll keep this chat clean and fun.\n"
            "Admins can use /features and /toggle <feature> to manage modules.\n"
            "Members can try /flirt or /points.\n\n"
            "Type /help to see all commands."
        ),
        parse_mode="HTML",
    )


async def handle_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    if query.data == "start:help":
        await query.answer()
        if query.message is not None:
            await query.message.edit_text(_help_text(), reply_markup=_start_keyboard(context))
        return

    if query.data == "start:about":
        await query.answer()
        if query.message is not None:
            await query.message.edit_text(_about_text(), reply_markup=_start_keyboard(context))


def register(application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_start_callback, pattern=r"^start:(help|about)$"))
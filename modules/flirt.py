from __future__ import annotations

import random
from collections import defaultdict

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command

MODULE_NAME = "flirt"
TRIGGERS = {
    "charming": {"beautiful", "gorgeous", "pretty", "lovely"},
    "intellectual": {"smart", "intelligent", "wise", "brilliant"},
    "romantic": {"sweet", "love", "adorable", "cute"},
}
RESPONSES = {
    "charming": [
        "Your charm is difficult to ignore.",
        "A dazzling presence like yours deserves a worthy response.",
        "You make elegance look effortless.",
        "There is a rare grace in the way you speak.",
        "Some people enter a room; you reshape it.",
        "Your smile has remarkable authority.",
        "A compelling aura follows you everywhere.",
        "You make refinement look natural.",
        "The whole conversation feels brighter now.",
        "You are as captivating as a rare manuscript.",
    ],
    "intellectual": [
        "That kind of mind deserves a careful answer.",
        "Your thoughts are the interesting part of the room.",
        "Curiosity looks good on you.",
        "You make logic feel unexpectedly elegant.",
        "A brilliant mind is always worth admiring.",
        "You are clearly the kind of person worth listening to.",
        "Sharp thoughts, sharp taste.",
        "That was perceptive, and I noticed.",
        "You think with rare clarity.",
        "There is something magnetic about intelligence done well.",
    ],
    "romantic": [
        "That was unexpectedly sweet.",
        "You make sincerity feel easy.",
        "A gentle heart leaves a strong impression.",
        "That was disarmingly warm.",
        "You have a way of softening the room.",
        "Your kindness is doing all the work here.",
        "That felt like a carefully written line.",
        "You have excellent romantic timing.",
        "That was charming in the best possible way.",
        "You know how to keep the mood memorable.",
    ],
}


def _match_category(text: str) -> str | None:
    lowered = text.lower()
    for category, trigger_words in TRIGGERS.items():
        if any(word in lowered for word in trigger_words):
            return category
    return None


async def _record_stats(context: ContextTypes.DEFAULT_TYPE, user_id: int, group_id: int, success: bool, trigger_word: str | None, response: str) -> None:
    db = get_runtime(context)["db"]
    row = await db.fetchone("SELECT attempts, successes, current_streak, best_streak FROM flirt_stats WHERE user_id = ? AND group_id = ?", (user_id, group_id))
    attempts = int(row[0]) + 1 if row else 1
    successes = int(row[1]) + 1 if row and success else (1 if success else 0)
    current_streak = int(row[2]) + 1 if row and success else 0
    best_streak = max(int(row[3]) if row else 0, current_streak)
    await db.execute(
        """
        INSERT INTO flirt_stats (user_id, group_id, attempts, successes, current_streak, best_streak, last_attempt_at)
        VALUES (?, ?, ?, ?, ?, ?, strftime('%s','now'))
        ON CONFLICT(user_id, group_id) DO UPDATE SET
            attempts = excluded.attempts,
            successes = excluded.successes,
            current_streak = excluded.current_streak,
            best_streak = excluded.best_streak,
            last_attempt_at = excluded.last_attempt_at
        """,
        (user_id, group_id, attempts, successes, current_streak, best_streak),
    )
    await db.execute(
        "INSERT INTO flirt_attempts (user_id, group_id, trigger_word, success, response) VALUES (?, ?, ?, ?, ?)",
        (user_id, group_id, trigger_word, 1 if success else 0, response),
    )


@feature_toggle("flirt")
@log_command
async def flirt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None:
        return
    text = " ".join(context.args or []) or (message.reply_to_message.text if message.reply_to_message and message.reply_to_message.text else "")
    category = _match_category(text)
    if category is None:
        await _record_stats(context, user.id, chat.id, False, None, "No trigger matched")
        await message.reply_text("🌸 That didn't quite land. Try again with a clearer compliment.")
        return
    response = random.choice(RESPONSES[category])
    await _record_stats(context, user.id, chat.id, True, category, response)
    await get_runtime(context)["event_bus"].publish(
        "points:add",
        {"context": context, "user_id": user.id, "group_id": chat.id, "points": 5, "reason": "flirt_success", "transaction_uid": f"flirt-{chat.id}-{user.id}-{text[:32]}"},
    )
    await message.reply_text(response)


@feature_toggle("flirt")
@log_command
async def flirt_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None:
        return
    row = await get_runtime(context)["db"].fetchone("SELECT attempts, successes, current_streak, best_streak FROM flirt_stats WHERE user_id = ? AND group_id = ?", (user.id, chat.id))
    if row is None:
        await message.reply_text("🌸 No flirt stats yet.")
        return
    attempts, successes, current_streak, best_streak = map(int, row)
    await message.reply_text(
        f"🌸 Flirt stats for {user.full_name}:\n• Attempts: {attempts}\n• Successes: {successes}\n• Current streak: {current_streak}\n• Best streak: {best_streak}"
    )


def register(application) -> None:
    application.add_handler(CommandHandler("flirt", flirt, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("flirt_stats", flirt_stats, filters=tg_filters.ChatType.GROUPS))

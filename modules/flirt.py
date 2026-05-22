from __future__ import annotations

import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command, require_acn_member

MODULE_NAME = "flirt"

TRIGGERS = {
    "beautiful",
    "elegant",
    "smart",
    "charming",
    "gorgeous",
    "amazing",
    "radiant",
}


def _is_successful_flirt(text: str) -> bool:
    normalized = text.lower()
    return any(token in normalized for token in TRIGGERS)


async def _update_flirt_stats(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    success: bool,
) -> tuple[int, int]:
    db = context.application.bot_data["db"]
    row = await db.fetchone(
        "SELECT attempts, successes FROM flirt_stats WHERE user_id = ?",
        (user_id,),
    )
    attempts = int(row["attempts"]) if row else 0
    successes = int(row["successes"]) if row else 0
    attempts += 1
    if success:
        successes += 1

    if row is None:
        await db.execute(
            "INSERT INTO flirt_stats (user_id, attempts, successes, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, attempts, successes, int(time.time())),
        )
    else:
        await db.execute(
            "UPDATE flirt_stats SET attempts = ?, successes = ?, updated_at = ? WHERE user_id = ?",
            (attempts, successes, int(time.time()), user_id),
        )
    return attempts, successes


@log_command
@require_acn_member
@feature_toggle("flirt")
async def flirt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    if not context.args:
        await msg.reply_text("Try: /flirt <message>")
        return

    text = " ".join(context.args)
    success = _is_successful_flirt(text)
    attempts, successes = await _update_flirt_stats(context, user.id, success)

    event_bus = context.application.bot_data["event_bus"]
    if success:
        await event_bus.publish(
            "points:add",
            {
                "user_id": user.id,
                "points": 5,
                "reason": "flirt_success",
            },
        )
        await event_bus.publish(
            "flirt:success",
            {
                "user_id": user.id,
                "text": text,
            },
        )
        await msg.reply_text(
            f"Nico Robin smiles. Flirt succeeded.\nSuccess rate: {successes}/{attempts}."
        )
    else:
        await msg.reply_text(
            f"Nico Robin raises an eyebrow. Try a gentler line.\nSuccess rate: {successes}/{attempts}."
        )


@log_command
@require_acn_member
@feature_toggle("flirt")
async def flirt_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    db = context.application.bot_data["db"]
    row = await db.fetchone(
        "SELECT attempts, successes FROM flirt_stats WHERE user_id = ?",
        (user.id,),
    )
    attempts = int(row["attempts"]) if row else 0
    successes = int(row["successes"]) if row else 0
    ratio = 0.0 if attempts == 0 else (successes / attempts) * 100
    await msg.reply_text(
        f"Flirt stats\nAttempts: {attempts}\nSuccesses: {successes}\nSuccess rate: {ratio:.1f}%"
    )


def register(application) -> None:
    application.add_handler(CommandHandler("flirt", flirt))
    application.add_handler(CommandHandler("flirt_stats", flirt_stats))

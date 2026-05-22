from __future__ import annotations

import random
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command, require_acn_member

MODULE_NAME = "friendship"

INTERACTIONS = [
    "Yamato grins and challenges you to train harder.",
    "Yamato shares a story about freedom and loyalty.",
    "Yamato nods and promises to stand by the crew.",
    "Yamato laughs and says your determination is inspiring.",
]


async def _get_bond(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> tuple[int, int]:
    db = context.application.bot_data["db"]
    row = await db.fetchone(
        "SELECT bond_points, last_interaction FROM friendship WHERE user_id = ?",
        (user_id,),
    )
    if row is None:
        await db.execute(
            "INSERT INTO friendship (user_id, bond_points, last_interaction) VALUES (?, 0, 0)",
            (user_id,),
        )
        return 0, 0
    return int(row["bond_points"]), int(row["last_interaction"])


@log_command
@require_acn_member
@feature_toggle("friendship")
async def bond_with_yamato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    db = context.application.bot_data["db"]
    points, last_interaction = await _get_bond(context, user.id)
    now = int(time.time())
    if now - last_interaction < 300:
        await msg.reply_text(
            "Yamato asks for a brief pause before the next bonding moment."
        )
        return

    gain = random.randint(2, 6)
    updated = points + gain
    await db.execute(
        "UPDATE friendship SET bond_points = ?, last_interaction = ? WHERE user_id = ?",
        (updated, now, user.id),
    )
    await msg.reply_text(
        f"Bond strengthened by {gain}. Current Yamato bond: {updated}."
    )


@log_command
@require_acn_member
@feature_toggle("friendship")
async def yamato_interact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    points, _ = await _get_bond(context, user.id)
    tier = "legendary" if points >= 200 else "strong" if points >= 80 else "growing"
    line = random.choice(INTERACTIONS)
    await msg.reply_text(f"{line}\nBond tier: {tier} ({points} points).")


def register(application) -> None:
    application.add_handler(CommandHandler("bond_with_yamato", bond_with_yamato))
    application.add_handler(CommandHandler("yamato_interact", yamato_interact))

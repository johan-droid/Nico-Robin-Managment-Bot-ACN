from __future__ import annotations

import random

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from utils.decorators import group_only


class NicoRobinMoments:
    """Collection of Nico Robin's best moments from One Piece"""

    MOMENTS = {
        "pat": [
            {
                "description": "Nico Robin gently pats someone's head",
                "gif_url": "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif",
                "context": "A sweet moment showing Robin's caring nature",
            },
            {
                "description": "Robin patting Chopper's head",
                "gif_url": "https://media.giphy.com/media/l4JzYya1y0m2JiGwI0/giphy.gif",
                "context": "Her gentle side with the crew",
            },
            {
                "description": "Robin comforting someone with a pat",
                "gif_url": "https://media.giphy.com/media/3o7aD6saalBwwftBIY8/giphy.gif",
                "context": "Always there to support her friends",
            },
            {
                "description": "Soft head pat from Robin",
                "gif_url": "https://media.giphy.com/media/1GDI1mlZy6vXa/giphy.gif",
                "context": "Her motherly instincts show through",
            },
        ],
        "slap": [
            {
                "description": "Nico Robin's iconic slap moment",
                "gif_url": "https://media.giphy.com/media/3o7aD4gYcB1M1qGg12/giphy.gif",
                "context": "When someone needs a reality check",
            },
            {
                "description": "Robin slapping some sense into someone",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "Her serious side when needed",
            },
            {
                "description": "Classic Robin slap",
                "gif_url": "https://media.giphy.com/media/3o7aD5ZQJ6s2vXqG8g/giphy.gif",
                "context": "Even the archaeologist has limits",
            },
        ],
        "hug": [
            {
                "description": "Nico Robin giving a warm hug",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "Rare moments of affection from the cool archaeologist",
            },
            {
                "description": "Robin hugging her crewmates",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "Showing her softer side",
            },
            {
                "description": "Comforting hug from Robin",
                "gif_url": "https://media.giphy.com/media/3o7aD4gYcB1M1qGg12/giphy.gif",
                "context": "When words aren't enough",
            },
        ],
        "smile": [
            {
                "description": "Nico Robin's rare genuine smile",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "When Robin truly smiles, it's magical",
            },
            {
                "description": "Robin's subtle smile",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "The archaeologist's quiet happiness",
            },
            {
                "description": "Robin laughing with the crew",
                "gif_url": "https://media.giphy.com/media/3o7aD4gYcB1M1qGg12/giphy.gif",
                "context": "Moments of pure joy",
            },
        ],
        "blush": [
            {
                "description": "Nico Robin blushing",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "Even the cool archaeologist can get flustered",
            },
            {
                "description": "Robin's cute blush moment",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "When she's embarrassed or shy",
            },
        ],
        "angry": [
            {
                "description": "Nico Robin's dangerous glare",
                "gif_url": "https://media.giphy.com/media/3o7aD4gYcB1M1qGg12/giphy.gif",
                "context": "When you've crossed the line",
            },
            {
                "description": "Robin's serious mode activated",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "The archaeologist means business",
            },
        ],
        "confused": [
            {
                "description": "Nico Robin looking confused",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "Even geniuses get confused sometimes",
            },
            {
                "description": "Robin's puzzled expression",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "When things don't make sense",
            },
        ],
        "dance": [
            {
                "description": "Nico Robin dancing",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "Letting loose on the ship",
            },
            {
                "description": "Robin's graceful dance moves",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "Elegant even when dancing",
            },
        ],
        "sleep": [
            {
                "description": "Nico Robin sleeping peacefully",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "Even archaeologists need their rest",
            },
            {
                "description": "Robin dozing off",
                "gif_url": "https://media.giphy.com/media/3o7aD2Qq6s2vXqG8g/giphy.gif",
                "context": "Peaceful moments on the Thousand Sunny",
            },
        ],
    }

    @classmethod
    def get_random_moment(cls, moment_type: str) -> dict:
        """Get a random moment of the specified type"""
        moments = cls.MOMENTS.get(moment_type, [])
        if not moments:
            # Return a default moment if type not found
            return {
                "description": "Nico Robin's mysterious smile",
                "gif_url": "https://media.giphy.com/media/3o7aD1ZQJ6s2vXqG8g/giphy.gif",
                "context": "The archaeologist's enigmatic nature",
            }
        return random.choice(moments)


def _get_user_mention(update: Update) -> str:
    """Get user mention for the action"""
    if (
        update.effective_message
        and update.effective_message.reply_to_message
        and update.effective_message.reply_to_message.from_user
    ):
        user = update.effective_message.reply_to_message.from_user
        return f"@{user.username}" if user.username else user.first_name
    elif update.effective_user:
        user = update.effective_user
        return f"@{user.username}" if user.username else user.first_name
    else:
        return "someone"


@group_only
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin pat GIF"""
    msg = update.effective_message
    if msg is None:
        return

    user_mention = _get_user_mention(update)
    moment = NicoRobinMoments.get_random_moment("pat")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin pats {user_mention}*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin gently pats {user_mention}\n\n{moment['description']}"
        )


@group_only
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin slap GIF"""
    msg = update.effective_message
    if msg is None:
        return

    user_mention = _get_user_mention(update)
    moment = NicoRobinMoments.get_random_moment("slap")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin slaps {user_mention}*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin slaps some sense into {user_mention}!\n\n{moment['description']}"
        )


@group_only
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin hug GIF"""
    msg = update.effective_message
    if msg is None:
        return

    user_mention = _get_user_mention(update)
    moment = NicoRobinMoments.get_random_moment("hug")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin hugs {user_mention}*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin gives {user_mention} a warm hug\n\n{moment['description']}"
        )


@group_only
async def robin_smile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin smile GIF"""
    msg = update.effective_message
    if msg is None:
        return

    moment = NicoRobinMoments.get_random_moment("smile")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin smiles*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(f"🌸 Nico Robin smiles gently\n\n{moment['description']}")


@group_only
async def robin_blush(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin blush GIF"""
    msg = update.effective_message
    if msg is None:
        return

    user_mention = _get_user_mention(update)
    moment = NicoRobinMoments.get_random_moment("blush")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin blushes at {user_mention}*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin blushes at {user_mention}\n\n{moment['description']}"
        )


@group_only
async def robin_angry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin angry GIF"""
    msg = update.effective_message
    if msg is None:
        return

    moment = NicoRobinMoments.get_random_moment("angry")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin is not amused*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin gives her dangerous glare\n\n{moment['description']}"
        )


@group_only
async def robin_confused(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin confused GIF"""
    msg = update.effective_message
    if msg is None:
        return

    moment = NicoRobinMoments.get_random_moment("confused")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin looks confused*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(f"🌸 Nico Robin looks puzzled\n\n{moment['description']}")


@group_only
async def robin_dance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin dance GIF"""
    msg = update.effective_message
    if msg is None:
        return

    moment = NicoRobinMoments.get_random_moment("dance")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin dances gracefully*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin shows her dance moves\n\n{moment['description']}"
        )


@group_only
async def robin_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Nico Robin sleeping GIF"""
    msg = update.effective_message
    if msg is None:
        return

    moment = NicoRobinMoments.get_random_moment("sleep")

    try:
        await msg.reply_animation(
            moment["gif_url"],
            caption=f"🌸 *Nico Robin is sleeping*\n\n{moment['description']}\n_{moment['context']}_",
            parse_mode="Markdown",
        )
    except Exception:
        # Fallback to text if GIF fails
        await msg.reply_text(
            f"🌸 Nico Robin is sleeping peacefully\n\n{moment['description']}"
        )


@group_only
async def robin_moments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all available Robin moment commands"""
    msg = update.effective_message
    if msg is None:
        return

    help_text = """
🌸 **Nico Robin Moments Commands:**

**Affectionate Moments:**
• `/pat` - Robin gently pats someone
• `/hug` - Robin gives a warm hug  
• `/robin_smile` - Robin's rare smile
• `/robin_blush` - Robin gets flustered

**Emotional Moments:**
• `/slap` - Robin's reality check slap
• `/robin_angry` - Robin's dangerous glare
• `/robin_confused` - Robin looks puzzled

**Fun Moments:**
• `/robin_dance` - Robin shows her moves
• `/robin_sleep` - Robin taking a nap

💡 *Reply to a message to target someone, or use it on yourself!*

Each command shows a different GIF moment from One Piece!
    """

    await msg.reply_text(help_text, parse_mode="Markdown")


def register(app) -> None:
    """Register all Nico Robin moment commands"""
    app.add_handler(CommandHandler("pat", pat))
    app.add_handler(CommandHandler("slap", slap))
    app.add_handler(CommandHandler("hug", hug))
    app.add_handler(CommandHandler("robin_smile", robin_smile))
    app.add_handler(CommandHandler("robin_blush", robin_blush))
    app.add_handler(CommandHandler("robin_angry", robin_angry))
    app.add_handler(CommandHandler("robin_confused", robin_confused))
    app.add_handler(CommandHandler("robin_dance", robin_dance))
    app.add_handler(CommandHandler("robin_sleep", robin_sleep))
    app.add_handler(CommandHandler("robin_moments", robin_moments))

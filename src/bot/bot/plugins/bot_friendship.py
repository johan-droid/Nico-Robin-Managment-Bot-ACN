from __future__ import annotations

import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.services.acn_service import acn_only
from src.bot.services.bot_friendship_service import bot_friendship_service


@acn_only
async def bond_with_yamato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bond with Yamato ACN bot"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    # Initialize friendship
    success = await bot_friendship_service.initialize_friendship(chat.id)

    if success:
        await msg.reply_text(
            "💕 **Nico Robin & Yamato ACN Friendship Bonded!**\n\n"
            "🌸 *Nico Robin*: Oh Yamato! I'm so happy to be friends with you!\n"
            "🗾 *Yamato ACN*: Robin-chan! I'll always be here for you!\n\n"
            "🎯 Use `/yamato_interact` to start sweet interactions!"
        )
    else:
        await msg.reply_text(
            "🌸 *smiles* Yamato and I are already friends in this group!"
        )


@acn_only
async def yamato_interact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Interact with Yamato ACN bot"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🌸 **Sweet Interactions with Yamato**\n\n"
            "**Available interactions:**\n"
            "• `waifu` - Compliment Yamato's waifu hunting skills\n"
            "• `compliment` - Give Yamato a sweet compliment\n"
            "• `moment` - Share a special moment together\n"
            "• `tease` - Playfully tease Yamato\n"
            "• `deep` - Share deep emotional connection\n\n"
            "🎯 Usage: `/yamato_interact <interaction_type>`\n"
            "💡 Example: `/yamato_interact waifu`"
        )
        return

    interaction_type = args[0].lower()
    interaction_mapping = {
        "waifu": "waifu_grab",
        "compliment": "compliment",
        "moment": "shared_moment",
        "tease": "playful_tease",
        "deep": "deep_connection",
    }

    mapped_type = interaction_mapping.get(interaction_type)
    if not mapped_type:
        await msg.reply_text(
            "❌ Unknown interaction type.\n"
            "Use `/yamato_interact` to see available options."
        )
        return

    # Process interaction
    result = await bot_friendship_service.process_bot_interaction(
        update, context, mapped_type, f"User initiated {interaction_type}"
    )

    if result["success"]:
        response = "🌸 **Nico Robin & Yamato Sweet Interaction**\n\n"
        response += f"🌸 **Nico Robin:** {result['nico_response']}\n\n"
        response += f"🗾 **Yamato ACN:** {result['yamato_response']}\n\n"
        response += f"💕 *Friendship Points: +{result['friendship_points']}*"

        await msg.reply_text(response, parse_mode="Markdown")
    else:
        await msg.reply_text(f"❌ {result.get('error', 'Unknown error')}")


@acn_only
async def yamato_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show friendship status with Yamato"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    status = await bot_friendship_service.get_friendship_status(chat.id)

    if status["status"] == "not_bonded":
        await msg.reply_text(
            "🌸 *looks around* I haven't bonded with Yamato ACN yet in this group!\n\n"
            "🎯 Use `/bond_with_yamato` to start our friendship!"
        )
        return

    # Format friendship status
    level_emojis = {
        "acquaintance": "👋",
        "friend": "🤝",
        "close_friend": "💕",
        "best_friend": "💖",
    }

    level_descriptions = {
        "acquaintance": "Just getting to know each other",
        "friend": "Good friends who enjoy time together",
        "close_friend": "Very close with deep connections",
        "best_friend": "Unbreakable bond, soulmates",
    }

    level = status["friendship_level"]
    emoji = level_emojis.get(level, "🌸")
    description = level_descriptions.get(level, "Unknown level")

    response = "💕 **Nico Robin & Yamato ACN Friendship**\n\n"
    response += f"{emoji} **Friendship Level:** {level.title()}\n"
    response += f"📝 *{description}*\n\n"
    response += f"📊 **Friendship Score:** {status['friendship_score']}/100\n"
    response += f"🤝 **Interactions:** {status['interaction_count']}\n"
    response += f"💭 **Shared Memories:** {status['shared_memories']}\n"
    response += f"😄 **Inside Jokes:** {status['inside_jokes']}\n"

    if status["last_interaction"] > 0:
        last_time = time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(status["last_interaction"])
        )
        response += f"🕐 **Last Interaction:** {last_time}\n"

    if status["bonded_at"] > 0:
        bonded_time = time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(status["bonded_at"])
        )
        response += f"💕 **Bonded Since:** {bonded_time}\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def yamato_memories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show shared memories with Yamato"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    limit = int(args[0]) if args and args[0].isdigit() else 10

    memories = await bot_friendship_service.get_shared_memories(chat.id, limit)

    if not memories:
        await msg.reply_text(
            "🌸 *thinking* Yamato and I haven't created any memories together yet!\n\n"
            "🎯 Use `/yamato_interact` to start making memories!"
        )
        return

    response = "💭 **Shared Memories with Yamato ACN**\n\n"

    memory_emojis = {
        "milestone": "🎯",
        "shared_experience": "🌟",
        "inside_joke": "😄",
        "adventure": "🗺️",
    }

    for memory in memories:
        emoji = memory_emojis.get(memory["memory_type"], "💭")
        memory_time = time.strftime("%Y-%m-%d", time.localtime(memory["memory_time"]))

        response += f"{emoji} **{memory['title']}**\n"
        response += f"   {memory['content']}\n"
        response += f"   📅 {memory_time} | ⭐ {memory['score']} pts\n\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def gift_to_yamato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a gift to Yamato"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    args = context.args or []
    if len(args) < 2:
        await msg.reply_text(
            "🎁 **Send a Gift to Yamato**\n\n"
            "**Available gifts:**\n"
            "• `flower` - Beautiful flower for Yamato\n"
            "• `book` - Ancient book as a gift\n"
            "• `sword` - Decorative sword for collection\n"
            "• `heart` - Heartfelt gift of love\n"
            "• `star` - Shining star for Yamato\n"
            "• `treasure` - Rare treasure as gift\n\n"
            "🎯 Usage: `/gift_to_yamato <gift_type> <message>`\n"
            "💡 Example: `/gift_to_yamato flower For my dear Yamato`"
        )
        return

    gift_type = args[0].lower()
    message = " ".join(args[1:])

    valid_gifts = ["flower", "book", "sword", "heart", "star", "treasure"]
    if gift_type not in valid_gifts:
        await msg.reply_text(
            f"❌ Invalid gift type. Choose from: {', '.join(valid_gifts)}"
        )
        return

    # Create gift
    success = await bot_friendship_service.create_companion_gift(
        group_id=chat.id,
        user_id=user.id,
        gift_type=gift_type,
        gift_name=f"{gift_type.title()} Gift",
        message=message,
    )

    if success:
        gift_emojis = {
            "flower": "🌸",
            "book": "📚",
            "sword": "⚔️",
            "heart": "❤️",
            "star": "⭐",
            "treasure": "💎",
        }

        emoji = gift_emojis[gift_type]

        await msg.reply_text(
            f"🎁 **Gift Sent to Yamato ACN!**\n\n"
            f"{emoji} **{gift_type.title()} Gift**\n"
            f"📝 *{message}*\n\n"
            f"🌸 *Nico Robin*: I hope Yamato likes this gift from me!\n"
            f"🗾 *Yamato ACN*: Robin-chan, this is so thoughtful! Thank you!"
        )
    else:
        await msg.reply_text("❌ Failed to send gift to Yamato.")


@acn_only
async def yamato_activities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent friendship activities"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    limit = int(args[0]) if args and args[0].isdigit() else 15

    activities = await bot_friendship_service.get_friendship_activities(chat.id, limit)

    if not activities:
        await msg.reply_text(
            "🌸 *smiles* No recent activities with Yamato yet!\n\n"
            "🎯 Use `/yamato_interact` to start activities!"
        )
        return

    response = "📊 **Recent Activities with Yamato ACN**\n\n"

    for activity in activities:
        activity_time = time.strftime("%H:%M", time.localtime(activity["timestamp"]))
        response += f"🕐 **{activity_time}** - {activity['interaction_type'].title()}\n"
        response += f"🌸 Robin: {activity['nico_response'][:50]}...\n"
        response += f"🗾 Yamato: {activity['yamato_response'][:50]}...\n"
        response += f"💕 +{activity['friendship_points']} pts\n\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def yamato_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Yamato friendship help"""
    msg = update.effective_message
    if msg is None:
        return

    help_text = """
💕 **Nico Robin & Yamato ACN Friendship Guide**

**Getting Started:**
• `/bond_with_yamato` - Bond with Yamato ACN bot
• `/yamato_status` - Show friendship status and level
• `/yamato_interact <type>` - Interact with Yamato

**Sweet Interactions:**
• `/yamato_interact waifu` - Compliment waifu hunting skills
• `/yamato_interact compliment` - Give sweet compliments
• `/yamato_interact moment` - Share special moments
• `/yamato_interact tease` - Playful teasing
• `/yamato_interact deep` - Deep emotional connection

**Friendship Features:**
• `/yamato_memories` - View shared memories
• `/gift_to_yamato <type> <msg>` - Send virtual gifts
• `/yamato_activities` - Recent friendship activities
• `/yamato_help` - Show this help

**Friendship Levels:**
👋 **Acquaintance** (0-24 pts) - Just getting to know each other
🤝 **Friend** (25-49 pts) - Good friends who enjoy time together
💕 **Close Friend** (50-74 pts) - Very close with deep connections
💖 **Best Friend** (75-100 pts) - Unbreakable bond, soulmates

**Gift Types:**
🌸 flower, 📚 book, ⚔️ sword, ❤️ heart, ⭐ star, 💎 treasure

🎯 **Tips:**
• Interact regularly to build friendship
• Earn friendship points with each interaction
• Create shared memories together
• Send thoughtful gifts to strengthen bonds
• Reach best friend level for special rewards!

💫 **Note:** This friendship is exclusive to ACN members only!
    """

    await msg.reply_text(help_text)


def register(app) -> None:
    pass
    """Register bot friendship commands"""

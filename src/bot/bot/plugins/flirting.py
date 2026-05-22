from __future__ import annotations

import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.database import async_session_factory
from src.bot.models.flirting import FlirtingAchievement, FlirtingStats
from src.bot.services.acn_service import acn_only
from src.bot.services.flirting_service import (
    get_flirting_service,
    process_flirting_command,
)
from src.bot.utils.formatters import telegram_user_label


@acn_only
async def flirt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main flirting command - process message for flirting response"""
    msg = update.effective_message
    if msg is None or not msg.text:
        return

    # Extract message content after command
    message_text = msg.text.replace("/flirt", "").strip()

    if not message_text:
        await msg.reply_text(
            "🌸 *adjusts glasses* You need to say something romantic!\n"
            "Try: `/flirt You have beautiful eyes`"
        )
        return

    # Process flirting attempt
    result = await process_flirting_command(update, context, message_text)

    if result["success"]:
        # Send successful response
        response = f"🌸 {result['response']}\n\n"
        response += f"✨ {result['success_response']}\n"
        if result["points_earned"] > 0:
            response += f"⭐ *Points earned: {result['points_earned']}*"

        await msg.reply_text(response, parse_mode="Markdown")

        # Check for achievements
        await _check_flirting_achievements(update, context, result)

    else:
        # Send failed response or error
        if "response" in result:
            await msg.reply_text(f"📖 {result['response']}")
        else:
            await msg.reply_text(
                "📖 *adjusts glasses* I'm not quite sure how to respond to that..."
            )


@acn_only
async def flirt_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's flirting statistics"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    async with async_session_factory() as session:
        # Get or create user stats
        from sqlalchemy import select

        result = await session.execute(
            select(FlirtingStats).where(
                FlirtingStats.user_id == user.id, FlirtingStats.group_id == chat.id
            )
        )
        stats = result.scalar_one_or_none()

        if not stats:
            await msg.reply_text(
                "🌸 *smiles gently* You haven't tried flirting with me yet!\n"
                "Use `/flirt <message>` to start."
            )
            return

        # Format stats response
        response = f"🌸 **{telegram_user_label(user)}'s Flirting Stats**\n\n"
        response += f"📊 **Level:** {stats.flirt_level.title()}\n"
        response += f"🎯 **Total Attempts:** {stats.total_attempts}\n"
        response += f"✅ **Successful:** {stats.successful_flirts}\n"
        response += f"❌ **Failed:** {stats.failed_flirts}\n"

        if stats.total_attempts > 0:
            success_rate = (stats.successful_flirts / stats.total_attempts) * 100
            response += f"📈 **Success Rate:** {success_rate:.1f}%\n"

        response += f"⭐ **Points Earned:** {stats.points_earned}\n"
        response += f"🔥 **Current Streak:** {stats.current_streak}\n"
        response += f"🏆 **Best Streak:** {stats.best_streak}\n"
        response += f"🌸 **Favorite Category:** {stats.favorite_category.title()}\n"
        response += f"🎓 **Highest Skill:** {stats.highest_skill_used.title()}\n"

        if stats.last_flirt_time > 0:
            last_flirt = time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(stats.last_flirt_time)
            )
            response += f"🕐 **Last Flirt:** {last_flirt}\n"

        await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def flirt_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available flirting categories"""
    msg = update.effective_message
    if msg is None:
        return

    flirting_service = get_flirting_service()
    categories = flirting_service.get_available_categories()

    response = "🌸 **Nico Robin's Flirting Categories**\n\n"

    category_emojis = {
        "charming": "🌸",
        "intellectual": "🧠",
        "mysterious": "🌙",
        "playful": "🎉",
        "romantic": "💕",
        "confident": "🔥",
    }

    for cat_id, cat_info in categories.items():
        emoji = category_emojis.get(cat_id, "🌸")
        response += f"{emoji} **{cat_info['name']}**\n"
        response += f"   {cat_info['description']}\n"
        response += f"   🎯 Difficulty: {cat_info['difficulty'].title()}\n"
        response += f"   📊 Success Rate: {cat_info['success_rate'] * 100:.0f}%\n\n"

    response += (
        "💡 **Tip:** Different categories work better with different approaches!\n"
    )
    response += "Try using words that match the category you want to trigger."

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def flirt_achievements(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show user's flirting achievements"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(FlirtingAchievement)
            .where(
                FlirtingAchievement.user_id == user.id,
                FlirtingAchievement.group_id == chat.id,
            )
            .order_by(FlirtingAchievement.unlocked_at.desc())
        )
        achievements = result.scalars().all()

        if not achievements:
            await msg.reply_text(
                "🌸 *smiles* You haven't earned any achievements yet!\n"
                "Keep flirting to unlock them!"
            )
            return

        response = f"🏆 **{telegram_user_label(user)}'s Flirting Achievements**\n\n"

        for achievement in achievements:
            unlocked_time = time.strftime(
                "%Y-%m-%d", time.localtime(achievement.unlocked_at)
            )
            response += f"{achievement.icon} **{achievement.achievement_name}**\n"
            response += f"   {achievement.description}\n"
            response += f"   ⭐ Points: {achievement.points_rewarded} | 📅 Unlocked: {unlocked_time}\n\n"

        await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def flirt_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show flirting help and tips"""
    msg = update.effective_message
    if msg is None:
        return

    help_text = """
🌸 **Nico Robin Flirting Guide**

**Basic Commands:**
• `/flirt <message>` - Try to flirt with Nico Robin
• `/flirt_stats` - View your flirting statistics
• `/flirt_categories` - See all flirting categories
• `/flirt_achievements` - View your achievements
• `/flirt_help` - Show this help

**Flirting Categories:**
🌸 **Charming** - Elegant compliments (Easy)
🧠 **Intellectual** - Smart conversations (Medium)
🌙 **Mysterious** - Enigmatic interactions (Hard)
🎉 **Playful** - Fun and teasing (Easy)
💕 **Romantic** - Deeply romantic (Medium)
🔥 **Confident** - Bold advances (Hard)

**Success Tips:**
• Use trigger words that match categories
• Higher ACN rank = better success rates
• Earn loyalty points for successful flirts
• Build streaks for bonus points
• Unlock achievements for special rewards

**Example Flirts:**
• `/flirt You have beautiful eyes` (Charming)
• `/flirt You're so intelligent` (Intellectual)
• `/flirt Tell me your secrets` (Mysterious)
• `/flirt You're making me blush` (Playful)
• `/flirt I think I'm falling for you` (Romantic)

🎯 **Remember:** Success depends on your ACN rank, points, and category difficulty!
    """

    await msg.reply_text(help_text)


@acn_only
async def flirt_example(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show example flirt lines"""
    msg = update.effective_message
    if msg is None:
        return

    get_flirting_service()

    examples = [
        {
            "category": "Charming",
            "examples": [
                "Your eyes are as beautiful as ancient artifacts",
                "You have a way with words that rivals poetry",
                "Your smile could light up the darkest ruins",
            ],
        },
        {
            "category": "Intellectual",
            "examples": [
                "I could discuss history with you all day",
                "Your mind is as vast as the Grand Line",
                "Let's explore knowledge together",
            ],
        },
        {
            "category": "Mysterious",
            "examples": [
                "I have secrets I only want to share with you",
                "Some mysteries are meant to be discovered together",
                "There's more to me than meets the eye",
            ],
        },
        {
            "category": "Playful",
            "examples": [
                "You bring out my playful side!",
                "Want to have a flirting competition?",
                "You're making this historian blush",
            ],
        },
        {
            "category": "Romantic",
            "examples": [
                "I think I'm falling for you",
                "My heart beats faster when you're near",
                "Forever with you sounds perfect",
            ],
        },
        {
            "category": "Confident",
            "examples": [
                "I know what I want... and I want you",
                "Desire is a dangerous game I'm willing to play",
                "You find me attractive, don't you?",
            ],
        },
    ]

    response = "🌸 **Example Flirt Lines**\n\n"

    for example_group in examples:
        response += f"**{example_group['category']}:**\n"
        for example in example_group["examples"]:
            response += f"• `/flirt {example}`\n"
        response += "\n"

    response += "💡 **Pro Tip:** Try these examples or create your own romantic lines!"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def flirt_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get a random flirt line"""
    msg = update.effective_message
    if msg is None:
        return

    flirting_service = get_flirting_service()
    random_line = flirting_service.get_random_flirt_line()

    response = "🌸 **Random Flirt Inspiration:**\n\n"
    response += f"{random_line}\n\n"
    response += "💡 Use this as inspiration for your own flirting attempts!"

    await msg.reply_text(response, parse_mode="Markdown")


async def _check_flirting_achievements(
    update: Update, context: ContextTypes.DEFAULT_TYPE, result: dict
) -> None:
    """Check and award flirting achievements"""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    async with async_session_factory() as session:
        from sqlalchemy import select

        # Get user stats
        stats_result = await session.execute(
            select(FlirtingStats).where(
                FlirtingStats.user_id == user.id, FlirtingStats.group_id == chat.id
            )
        )
        stats = stats_result.scalar_one_or_none()

        if not stats:
            return

        # Check for achievement conditions
        achievements_to_check = []

        # First flirt achievement
        if stats.total_attempts == 1:
            achievements_to_check.append(
                {
                    "type": "first_flirt",
                    "name": "First Flutter",
                    "description": "Made your first flirting attempt with Nico Robin",
                    "icon": "🌸",
                    "points": 10,
                }
            )

        # Successful flirt achievement
        if stats.successful_flirts == 1:
            achievements_to_check.append(
                {
                    "type": "successful_flirt",
                    "name": "Charming Success",
                    "description": "Successfully flirted with Nico Robin for the first time",
                    "icon": "✨",
                    "points": 15,
                }
            )

        # Milestone achievements
        if stats.total_attempts == 10:
            achievements_to_check.append(
                {
                    "type": "ten_flirts",
                    "name": "Persistent Admirer",
                    "description": "Made 10 flirting attempts",
                    "icon": "💯",
                    "points": 25,
                }
            )
        elif stats.total_attempts == 50:
            achievements_to_check.append(
                {
                    "type": "fifty_flirts",
                    "name": "Dedicated Suitor",
                    "description": "Made 50 flirting attempts",
                    "icon": "🔥",
                    "points": 100,
                }
            )
        elif stats.total_attempts == 100:
            achievements_to_check.append(
                {
                    "type": "hundred_flirts",
                    "name": "Ultimate Flirt",
                    "description": "Made 100 flirting attempts",
                    "icon": "👑",
                    "points": 200,
                }
            )

        # Streak achievements
        if stats.current_streak == 5 and stats.best_streak >= 5:
            achievements_to_check.append(
                {
                    "type": "streak_5",
                    "name": "Hot Streak",
                    "description": "Achieved a 5-flirt success streak",
                    "icon": "🔥",
                    "points": 30,
                }
            )
        elif stats.current_streak == 10 and stats.best_streak >= 10:
            achievements_to_check.append(
                {
                    "type": "streak_10",
                    "name": "On Fire",
                    "description": "Achieved a 10-flirt success streak",
                    "icon": "💥",
                    "points": 60,
                }
            )

        # Award achievements
        for achievement_data in achievements_to_check:
            # Check if already earned
            existing = await session.execute(
                select(FlirtingAchievement).where(
                    FlirtingAchievement.user_id == user.id,
                    FlirtingAchievement.group_id == chat.id,
                    FlirtingAchievement.achievement_type == achievement_data["type"],
                )
            )

            if not existing.scalar_one_or_none():
                # Create new achievement
                achievement = FlirtingAchievement(
                    user_id=user.id,
                    group_id=chat.id,
                    achievement_type=achievement_data["type"],
                    achievement_name=achievement_data["name"],
                    description=achievement_data["description"],
                    icon=achievement_data["icon"],
                    points_rewarded=achievement_data["points"],
                    unlocked_at=int(time.time()),
                )
                session.add(achievement)

                # Award loyalty points
                from src.bot.services.acn_service import ACNService

                await ACNService.add_loyalty_points(
                    session=session,
                    user_id=user.id,
                    group_id=chat.id,
                    points=achievement_data["points"],
                    activity_type="achievement",
                    action=f"flirting_achievement_{achievement_data['type']}",
                    metadata=f"achievement: {achievement_data['name']}",
                )

                # Send achievement notification
                if update.effective_message:
                    await update.effective_message.reply_text(
                        f"🏆 **Achievement Unlocked!**\n\n"
                        f"{achievement_data['icon']} **{achievement_data['name']}**\n"
                        f"{achievement_data['description']}\n"
                        f"⭐ *Bonus Points: {achievement_data['points']}*",
                        parse_mode="Markdown",
                    )

        await session.commit()


def register(app) -> None:
    """Register flirting commands"""
    app.add_handler(CommandHandler("flirt", flirt))
    app.add_handler(CommandHandler("flirt_stats", flirt_stats))
    app.add_handler(CommandHandler("flirt_categories", flirt_categories))
    app.add_handler(CommandHandler("flirt_achievements", flirt_achievements))
    app.add_handler(CommandHandler("flirt_help", flirt_help))
    app.add_handler(CommandHandler("flirt_example", flirt_example))
    app.add_handler(CommandHandler("flirt_random", flirt_random))

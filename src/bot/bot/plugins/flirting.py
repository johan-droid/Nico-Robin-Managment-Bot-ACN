from __future__ import annotations

import random
import time
from collections.abc import Iterable

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.database import async_session_factory
from src.bot.models.flirting import FlirtingAchievement, FlirtingAttempt, FlirtingStats
from src.bot.services.acn_service import acn_only
from src.bot.utils.formatters import telegram_user_label


FLIRT_RESPONSES: dict[str, list[str]] = {
    "charming": [
        "You have beautiful eyes, and I don't say that lightly.",
        "Gorgeous is the only word that feels accurate right now.",
        "Your smile makes the whole room feel softer.",
        "Beautiful people are common; beautiful souls are rare.",
        "You look absolutely radiant today.",
        "I could admire your elegance for hours.",
        "There is a certain grace to you that is hard to ignore.",
        "You make charm look effortless.",
        "I think gorgeous was invented for moments like this.",
        "Your presence is as lovely as a calm sunrise.",
        "You have a striking kind of beauty.",
        "Some compliments are obvious, and beautiful is one of them.",
    ],
    "intellectual": [
        "Smart is attractive, but your curiosity is even better.",
        "You sound intelligent enough to keep up with my favorite discussions.",
        "I like a mind that asks difficult questions.",
        "There is something irresistible about someone who loves learning.",
        "Your intelligence makes the conversation much more interesting.",
        "I suspect your thoughts are as sharp as your words.",
        "A brilliant mind deserves proper appreciation.",
        "You make intelligence look very charming.",
        "Smart choices begin with smart company.",
        "I enjoy people who can surprise me with their ideas.",
        "Intelligent answers are my favorite kind of flirting.",
        "You seem like someone worth discussing everything with.",
    ],
}

FLIRT_TRIGGERS: dict[str, list[str]] = {
    "charming": ["beautiful", "gorgeous", "lovely", "pretty", "radiant"],
    "intellectual": ["smart", "intelligent", "clever", "brilliant", "wise"],
}

FLIRT_METADATA: dict[str, dict[str, object]] = {
    "charming": {"success_rate": 0.8, "skill_level": "beginner", "points": 5},
    "intellectual": {
        "success_rate": 0.7,
        "skill_level": "intermediate",
        "points": 7,
    },
}

SKILL_ORDER = ["beginner", "intermediate", "advanced", "expert", "master"]


def _normalize_message_text(text: str) -> str:
    return " ".join(text.lower().split())


def _match_flirt_category(message_text: str) -> str | None:
    normalized = _normalize_message_text(message_text)
    best_category = None
    best_score = 0

    for category, triggers in FLIRT_TRIGGERS.items():
        score = sum(1 for trigger in triggers if trigger in normalized)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category if best_score > 0 else None


def _pick_flirt_response(category: str) -> str:
    return random.choice(FLIRT_RESPONSES[category])


def _skill_rank(skill_level: str) -> int:
    try:
        return SKILL_ORDER.index(skill_level)
    except ValueError:
        return 0


def _update_flirt_stats(
    stats: FlirtingStats,
    *,
    success: bool,
    category: str,
    skill_level: str,
    points_earned: int,
) -> None:
    stats.total_attempts += 1
    if success:
        stats.successful_flirts += 1
        stats.current_streak += 1
        stats.best_streak = max(stats.best_streak, stats.current_streak)
        stats.favorite_category = category
        stats.highest_skill_used = (
            skill_level
            if _skill_rank(skill_level) >= _skill_rank(stats.highest_skill_used)
            else stats.highest_skill_used
        )
        stats.points_earned += points_earned
    else:
        stats.failed_flirts += 1
        stats.current_streak = 0
    stats.success_rate = (
        (stats.successful_flirts / stats.total_attempts) * 100
        if stats.total_attempts
        else 0.0
    )
    stats.last_flirt_time = int(time.time())
    stats.flirt_level = (
        "master"
        if stats.best_streak >= 10
        else "expert"
        if stats.best_streak >= 5
        else "intermediate"
        if stats.successful_flirts >= 3
        else "novice"
    )


async def _get_or_create_flirt_stats(
    session, user_id: int, group_id: int
) -> FlirtingStats:
    from sqlalchemy import select

    result = await session.execute(
        select(FlirtingStats).where(
            FlirtingStats.user_id == user_id, FlirtingStats.group_id == group_id
        )
    )
    stats = result.scalar_one_or_none()
    if stats is not None:
        return stats

    stats = FlirtingStats(
        user_id=user_id,
        group_id=group_id,
        total_attempts=0,
        successful_flirts=0,
        failed_flirts=0,
        favorite_category="charming",
        highest_skill_used="beginner",
        points_earned=0,
        success_rate=0.0,
        current_streak=0,
        best_streak=0,
        last_flirt_time=0,
        flirt_level="novice",
    )
    session.add(stats)
    await session.flush()
    return stats


async def _record_flirt_attempt(
    *,
    user_id: int,
    group_id: int,
    message_text: str,
    category: str,
    success: bool,
    response_given: str,
    points_earned: int,
    skill_level: str,
) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            stats = await _get_or_create_flirt_stats(session, user_id, group_id)
            _update_flirt_stats(
                stats,
                success=success,
                category=category,
                skill_level=skill_level,
                points_earned=points_earned,
            )

            session.add(
                FlirtingAttempt(
                    user_id=user_id,
                    group_id=group_id,
                    target_user_id=None,
                    event_id=f"manual_{category}_{stats.total_attempts}",
                    category=category,
                    message_text=message_text,
                    successful=success,
                    response_given=response_given,
                    points_earned=points_earned,
                    attempt_time=int(time.time()),
                    skill_level=skill_level,
                )
            )


@acn_only
async def flirt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main flirting command - process message for flirting response"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None or not msg.text:
        return

    # Extract message content after command
    message_text = msg.text.split(maxsplit=1)[1].strip() if " " in msg.text else ""

    if not message_text:
        await msg.reply_text(
            "🌸 *adjusts glasses* You need to say something romantic!\n"
            "Try: `/flirt You have beautiful eyes`"
        )
        return

    category = _match_flirt_category(message_text)
    if category is None:
        response = "🌸 *smiles thoughtfully* That needs a more romantic angle. Try beautiful or smart, perhaps?"
        await _record_flirt_attempt(
            user_id=user.id,
            group_id=chat.id,
            message_text=message_text,
            category="charming",
            success=False,
            response_given=response,
            points_earned=0,
            skill_level="beginner",
        )
        await msg.reply_text(response)
        return

    response = _pick_flirt_response(category)
    metadata = FLIRT_METADATA[category]
    base_success_rate = float(metadata["success_rate"])
    success = random.random() < base_success_rate
    points_earned = int(metadata["points"]) if success else 0
    skill_level = str(metadata["skill_level"])

    await _record_flirt_attempt(
        user_id=user.id,
        group_id=chat.id,
        message_text=message_text,
        category=category,
        success=success,
        response_given=response,
        points_earned=points_earned,
        skill_level=skill_level,
    )

    if success:
        output = f"🌸 {response}\n\n✨ *You found the right words.*\n"
        if points_earned > 0:
            output += f"⭐ *Points earned: {points_earned}*"
        await msg.reply_text(output, parse_mode="Markdown")
        await _check_flirting_achievements(update, context, {"category": category})
    else:
        await msg.reply_text(f"📖 {response}")


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

        response += f"📈 **Success Rate:** {stats.success_rate:.1f}%\n"

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

    response = "🌸 **Nico Robin's Flirting Categories**\n\n"

    category_labels = {
        "charming": "🌸 Charming",
        "intellectual": "🧠 Intellectual",
    }

    for cat_id, triggers in FLIRT_TRIGGERS.items():
        response += f"{category_labels.get(cat_id, cat_id.title())}\n"
        response += f"   Trigger words: {', '.join(triggers)}\n"
        response += f"   Responses: {len(FLIRT_RESPONSES[cat_id])}\n\n"

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

    category = random.choice(list(FLIRT_RESPONSES.keys()))
    random_line = _pick_flirt_response(category)

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

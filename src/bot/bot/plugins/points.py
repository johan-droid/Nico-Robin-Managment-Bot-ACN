from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.services.acn_service import acn_only
from src.bot.services.point_service import point_service
from src.bot.utils.decorators import admin_only
from src.bot.utils.formatters import telegram_user_label


@acn_only
async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's point balance and level"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Get user points
    points_info = await point_service.get_user_points(user.id, chat.id)

    if not points_info:
        await msg.reply_text(
            "🌸 *smiles* Welcome to the ACN Point System!\n\n"
            "🎯 You've been awarded **50 points** as a welcome bonus!\n"
            "💫 Start earning points by participating in the group!"
        )
        return

    # Format point information
    level_emojis = {
        1: "📚",
        2: "🗺️",
        3: "🏺",
        4: "📜",
        5: "🌺",
        6: "🎶",
        7: "💎",
        8: "⭐",
        9: "👑",
        10: "🏆",
    }

    emoji = level_emojis.get(points_info["level"], "🌸")

    response = f"💫 **{telegram_user_label(user)}'s Point Balance**\n\n"
    response += (
        f"{emoji} **Level {points_info['level']} - {points_info['level_name']}**\n"
    )
    response += f"💎 **Current Points:** {points_info['current_points']:,}\n"
    response += f"📈 **Total Earned:** {points_info['total_earned']:,}\n"
    response += f"💸 **Total Spent:** {points_info['total_spent']:,}\n"
    response += f"⚡ **Experience:** {points_info['experience']:,}\n"
    response += f"🔥 **Streak Days:** {points_info['streak_days']}\n"
    response += f"💰 **Bonus Multiplier:** {points_info['bonus_multiplier']:.1f}x\n"

    if points_info["selected_apploid"]:
        response += f"🎭 **Selected Apploid:** {points_info['selected_apploid']}\n"

    if points_info["next_level_points"] > 0:
        needed = points_info["next_level_points"] - points_info["total_earned"]
        response += f"🎯 **Next Level:** {needed:,} points needed\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show point leaderboard"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    limit = int(args[0]) if args and args[0].isdigit() else 10

    # Get leaderboard
    leaderboard = await point_service.get_leaderboard(chat.id, limit)

    if not leaderboard:
        await msg.reply_text(
            "🌸 *looks around* No one has earned points yet!\n\n"
            "🎯 Start participating to earn points and climb the leaderboard!"
        )
        return

    response = "🏆 **ACN Point Leaderboard**\n\n"

    rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

    for entry in leaderboard:
        rank_emoji = rank_emojis.get(entry["rank"], f"#{entry['rank']}")
        apploid_emoji = entry.get("selected_apploid", "🌸")

        response += f"{rank_emoji} **{apploid_emoji} User {entry['user_id']}**\n"
        response += f"   💎 {entry['points']:,} pts | Lv.{entry['level']} {entry['level_name']}\n\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def apploids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available and owned apploids"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Get owned apploids
    owned_apploids = await point_service.get_user_apploids(user.id, chat.id)

    # Get available apploids
    available_apploids = await point_service.get_available_apploids(user.id, chat.id)

    response = f"🎭 **{telegram_user_label(user)}'s Apploids**\n\n"

    # Show owned apploids
    if owned_apploids:
        response += "💎 **Owned Apploids:**\n"
        for apploid in owned_apploids:
            equip_status = "✅ Equipped" if apploid["is_equipped"] else "📦 Owned"
            response += f"  {apploid['emoji']} **{apploid['name']}** - {apploid['rarity']} ({equip_status})\n"
        response += "\n"

    # Show available apploids
    if available_apploids:
        response += "🛍️ **Available Apploids:**\n"
        for apploid in available_apploids[:10]:  # Show top 10
            rarity_emoji = {
                "common": "⚪",
                "rare": "🔵",
                "epic": "🟣",
                "legendary": "🟡",
            }
            emoji = rarity_emoji.get(apploid["rarity"], "⚪")

            response += f"  {emoji} {apploid['emoji']} **{apploid['name']}**\n"
            response += f"     💰 {apploid['required_points']} pts | Lv.{apploid['required_level']}\n"
            response += f"     📝 {apploid['description']}\n\n"

        if len(available_apploids) > 10:
            response += f"... and {len(available_apploids) - 10} more apploids!\n"
    else:
        response += "🌸 *smiles* No apploids available for your level.\n"
        response += "🎯 Keep earning points and leveling up to unlock more!\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def buy_apploid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Purchase an apploid"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🛍️ **Purchase Apploid**\n\n"
            "🎯 Usage: `/buy_apploid <apploid_name>`\n\n"
            "💡 Use `/apploids` to see available apploids!"
        )
        return

    apploid_name = " ".join(args)

    # Purchase apploid
    success, message = await point_service.purchase_apploid(
        user.id, chat.id, apploid_name
    )

    if success:
        await msg.reply_text(f"🎉 **Purchase Successful!**\n\n{message}")
    else:
        await msg.reply_text(f"❌ **Purchase Failed**\n\n{message}")


@acn_only
async def equip_apploid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Equip an apploid"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🎭 **Equip Apploid**\n\n"
            "🎯 Usage: `/equip_apploid <apploid_name>`\n\n"
            "💡 Use `/apploids` to see your owned apploids!"
        )
        return

    apploid_name = " ".join(args)

    # Equip apploid
    success, message = await point_service.equip_apploid(user.id, chat.id, apploid_name)

    if success:
        await msg.reply_text(f"✨ **Equipped Successfully!**\n\n{message}")
    else:
        await msg.reply_text(f"❌ **Equip Failed**\n\n{message}")


@acn_only
async def point_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show point statistics for the group"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    # Get group statistics
    stats = await point_service.get_point_stats(chat.id)

    response = "📊 **Group Point Statistics**\n\n"
    response += f"👥 **Total Users:** {stats['total_users']}\n"
    response += f"💎 **Total Points:** {stats['total_points']:,}\n"
    response += f"📈 **Total Earned:** {stats['total_earned']:,}\n"
    response += f"💸 **Total Spent:** {stats['total_spent']:,}\n"
    response += f"📊 **Average Points:** {stats['average_points']:,}\n"
    response += f"🏆 **Highest Level:** {stats['highest_level']}\n"
    response += f"🎭 **Apploids Owned:** {stats['apploids_owned']}\n"

    await msg.reply_text(response, parse_mode="Markdown")


@admin_only
async def award_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Award points to a user."""

    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 2:
        await msg.reply_text(
            "🌸 Usage: `/award <user_id> <points> [reason]`",
            parse_mode="Markdown",
        )
        return

    try:
        user_id = int(args[0])
        points_value = int(args[1])
    except ValueError:
        await msg.reply_text("🌸 Invalid user ID or points format.")
        return

    if points_value <= 0:
        await msg.reply_text("🌸 Points must be positive.")
        return

    reason = " ".join(args[2:]) if len(args) > 2 else "Manual award"
    success, message = await point_service.add_points(
        user_id,
        points_value,
        reason,
        group_id=chat.id,
        source="award",
        cooldown_seconds=0,
    )

    if success:
        points_info = await point_service.get_user_points(user_id, chat.id)
        balance_text = (
            f"\n💎 New total: {points_info['current_points']:,} points"
            if points_info
            else ""
        )
        await msg.reply_text(
            f"🌸 **Points Awarded**\n\n"
            f"✅ User {user_id} received {points_value} points\n"
            f"📝 Reason: {reason}{balance_text}",
            parse_mode="Markdown",
        )
        return

    await msg.reply_text(f"🌸 {message}")


@admin_only
async def recalculate_points(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Rebuild point balances from stored transactions."""

    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    target_user_id: int | None = None
    if args:
        try:
            target_user_id = int(args[0])
        except ValueError:
            await msg.reply_text("🌸 Usage: `/recalculate_points [user_id]`", parse_mode="Markdown")
            return

    summary = await point_service.recalculate_group_points(chat.id, target_user_id)

    if target_user_id is not None:
        points_info = await point_service.get_user_points(target_user_id, chat.id)
        if points_info:
            await msg.reply_text(
                f"🌸 Recalculated user {target_user_id}.\n"
                f"💎 Balance: {points_info['current_points']:,}\n"
                f"📈 Earned: {points_info['total_earned']:,}\n"
                f"💸 Spent: {points_info['total_spent']:,}",
            )
            return

    await msg.reply_text(
        f"🌸 Recalculated {summary['updated_users']} users.\n"
        f"💎 Total points: {summary['current_points']:,}\n"
        f"📈 Total earned: {summary['total_earned']:,}\n"
        f"💸 Total spent: {summary['total_spent']:,}",
    )


@acn_only
async def earn_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show ways to earn points"""
    msg = update.effective_message
    if msg is None:
        return

    help_text = """
💫 **How to Earn Points** 🌸

**🎯 Daily Activities:**
• Send messages (1 pt per message, 1 min cooldown)
• Daily streak bonus (10 pts, 24h cooldown)
• Weekly streak bonus (50 pts, 7 days cooldown)

**🎮 Interactive Features:**
• Successful flirting (5 pts, 5 min cooldown)
• Bot friendship interactions (3 pts, 10 min cooldown)
• Helpful contributions (8 pts, 1h cooldown)
• Creative content (12 pts, 2h cooldown)
• Social interactions (6 pts, 30 min cooldown)

**🏆 Achievements:**
• Earn achievements (20 pts, no cooldown)
• Special bonuses (15 pts, no cooldown)

**💰 Level Benefits:**
• Higher levels = Point bonuses
• Level 2: 1.1x multiplier
• Level 5: 1.4x multiplier
• Level 8: 1.8x multiplier
• Level 10: 2.5x multiplier

**🎭 Collect Apploids:**
• Common apploids: 50-300 pts
• Rare apploids: 500-1500 pts
• Epic apploids: 1500-3500 pts
• Legendary apploids: 8000-25000 pts

**📈 Point Usage:**
• Purchase apploids to customize your profile
• Unlock special rewards and features
• Climb the leaderboard
• Show off your collection!

💡 **Pro Tips:**
• Maintain daily streaks for bonus points
• Level up to earn more points per activity
• Collect rare apploids to show off
• Participate regularly to maximize earnings

🌸 *Nico Robin*: "Knowledge is power, and points are treasure!"
    """

    await msg.reply_text(help_text)


@acn_only
async def point_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show point system help"""
    msg = update.effective_message
    if msg is None:
        return

    help_text = """
💫 **ACN Point System Help** 🌸

**📊 Point Commands:**
• `/points` - Show your point balance and level
• `/leaderboard [limit]` - Show top point earners
• `/award <user_id> <points> [reason]` - award points to a user
• `/recalculate_points [user_id]` - rebuild balances from transactions
• `/apploids` - View owned and available apploids
• `/buy_apploid <name>` - Purchase an apploid
• `/equip_apploid <name>` - Equip an apploid
• `/point_stats` - Group point statistics
• `/earn_points` - Show ways to earn points
• `/point_help` - Show this help

**🎭 Apploid System:**
• Collect unique Nico Robin themed apploids
• Equip apploids to customize your profile
• Different rarities: Common, Rare, Epic, Legendary
• Higher levels unlock better apploids

**🏆 Level System:**
• 10 levels from Novice to Legendary Scholar
• Higher levels = point bonuses
• Level requirements based on total earned points
• Special perks at higher levels

**💰 Point Earning:**
• Multiple ways to earn points
• Cooldowns prevent spam
• Bonus multipliers for higher levels
• Special events and bonuses

**📈 Progress Tracking:**
• Personal point statistics
• Group leaderboards
• Achievement tracking
• Streak bonuses

🎯 **Getting Started:**
1. Use `/points` to see your balance
2. Use `/earn_points` to learn how to earn
3. Use `/apploids` to browse apploids
4. Start participating to earn points!

💫 **Note:** Point system is exclusive to ACN members!
    """

    await msg.reply_text(help_text)


def register(app) -> None:
    """Register point system commands"""
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("award", award_points))
    app.add_handler(CommandHandler("recalculate_points", recalculate_points))
    app.add_handler(CommandHandler("apploids", apploids))
    app.add_handler(CommandHandler("buy_apploid", buy_apploid))
    app.add_handler(CommandHandler("equip_apploid", equip_apploid))
    app.add_handler(CommandHandler("point_stats", point_stats))
    app.add_handler(CommandHandler("earn_points", earn_points))
    app.add_handler(CommandHandler("point_help", point_help))

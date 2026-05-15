from __future__ import annotations

import time
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database import async_session_factory
from services.acn_service import (
    ACNService,
    acn_only,
    admin_captain_commander_only,
    captain_commander_only,
)
from utils.formatters import telegram_user_label


@acn_only
async def acn_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check ACN status and loyalty points"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            # Get user role
            role = await ACNService.get_user_role(user.id)

            # Get loyalty points
            loyalty_points = await ACNService.get_loyalty_points(
                session, user.id, chat.id
            )

            # Format response
            if role == "captain":
                role_text = "⚓ **Captain** - Monkey D. Sparrow"
            elif role == "commander":
                role_text = "🎖️ **Commander**"
            elif role == "member":
                role_text = "⭐ **ACN Member**"
            else:
                role_text = "👤 **Member**"

            points_text = f"{loyalty_points.points} pts" if loyalty_points else "0 pts"
            rank_text = loyalty_points.rank if loyalty_points else "Crew Member"

            response = f"🌸 **ACN Status for {telegram_user_label(user)}**\n\n"
            response += f"📋 **Role:** {role_text}\n"
            response += f"💎 **Rank:** {rank_text}\n"
            response += f"⭐ **Points:** {points_text}\n"

            if loyalty_points and loyalty_points.total_actions > 0:
                response += f"📊 **Actions:** {loyalty_points.total_actions}\n"
                response += f"🕐 **Last Activity:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(loyalty_points.last_activity))}\n"

            await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def loyalty_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show loyalty points leaderboard for the group"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            # Get all members with loyalty points
            members = await ACNService.get_group_members(session, chat.id)

            if not members:
                await msg.reply_text("🌸 No ACN members found in this group.")
                return

            # Sort by points
            members.sort(key=lambda x: x["points"], reverse=True)

            # Format leaderboard
            response = "🏆 **ACN Loyalty Leaderboard**\n\n"

            for i, member in enumerate(members[:10], 1):  # Top 10
                medal = (
                    "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                )
                role_icon = (
                    "⚓"
                    if member["role"] == "captain"
                    else "🎖️" if member["role"] == "commander" else "⭐"
                )

                response += f"{medal} {role_icon} **{member['username']}**\n"
                response += f"   💎 {member['rank']} • ⭐ {member['points']} pts\n\n"

            await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def add_acn_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add group to ACN whitelist (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            # Check if already whitelisted
            if await ACNService.is_acn_group(chat.id):
                await msg.reply_text("🌸 This group is already whitelisted for ACN.")
                return

            # Add to whitelist
            await ACNService.add_to_whitelist(
                session=session,
                entity_id=chat.id,
                entity_name=chat.title or f"Group {chat.id}",
                whitelist_type="group",
                role="acn_group",
                added_by=user.id,
                notes="Added by ACN leadership",
            )

            await msg.reply_text(
                f"🌸 **Group Whitelisted!**\n\n"
                f"✅ {chat.title} is now an official ACN group.\n"
                f"🎯 Bot will work exclusively for ACN members here."
            )


@captain_commander_only
async def add_acn_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add user to ACN whitelist (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 2:
        await msg.reply_text(
            "🌸 Usage: `/addacn <user_id_or_username> <role>\n"
            "Roles: captain, commander, member, ally"
        )
        return

    user_identifier = args[0]
    role = args[1].lower()

    if role not in ["captain", "commander", "member", "ally"]:
        await msg.reply_text(
            "🌸 Invalid role. Use: captain, commander, member, or ally"
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            # Try to resolve user
            user_id = None
            username = None

            try:
                # If it's a number, treat as user_id
                if user_identifier.isdigit():
                    user_id = int(user_identifier)
                    # Try to get username from Telegram
                    try:
                        tg_user = await context.bot.get_chat_member(chat.id, user_id)
                        if tg_user.user.username:
                            username = tg_user.user.username
                        else:
                            username = tg_user.user.first_name
                    except Exception:
                        username = f"User {user_id}"
                else:
                    # Search for user by username in group
                    username = user_identifier.lstrip("@")
                    await msg.reply_text(
                        "🌸 Please use user ID instead of username for now."
                    )
                    return
            except Exception as e:
                await msg.reply_text(f"🌸 Error resolving user: {str(e)}")
                return

            # Add to whitelist
            await ACNService.add_to_whitelist(
                session=session,
                entity_id=user_id,
                entity_name=username,
                whitelist_type="user",
                role=role,
                added_by=update.effective_user.id if update.effective_user else None,
                notes=f"Added by ACN leadership with role: {role}",
            )

            await msg.reply_text(
                f"🌸 **ACN Member Added!**\n\n"
                f"✅ {username} is now an ACN {role}.\n"
                f"🎯 They can use the bot in all ACN groups."
            )


@captain_commander_only
async def remove_acn_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove user from ACN whitelist (Captain/Commander only)"""
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text("🌸 Usage: `/removeacn <user_id>")
        return

    user_identifier = args[0]

    try:
        user_id = int(user_identifier) if user_identifier.isdigit() else None
        if not user_id:
            await msg.reply_text("🌸 Please provide a valid user ID.")
            return
    except ValueError:
        await msg.reply_text("🌸 Invalid user ID format.")
        return

    async with async_session_factory() as session:
        async with session.begin():
            # Remove from whitelist
            removed = await ACNService.remove_from_whitelist(
                session=session, entity_id=user_id, whitelist_type="user"
            )

            if removed:
                await msg.reply_text(
                    f"🌸 **ACN Member Removed!**\n\n"
                    f"✅ User {user_id} is no longer an ACN member.\n"
                    f"🚫 They cannot use the bot in ACN groups."
                )
            else:
                await msg.reply_text("🌸 User not found in ACN whitelist.")


@acn_only
async def acn_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all ACN members in the group"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            members = await ACNService.get_group_members(session, chat.id)

            if not members:
                await msg.reply_text("🌸 No ACN members found in this group.")
                return

            # Group members by role
            captains = [m for m in members if m["role"] == "captain"]
            commanders = [m for m in members if m["role"] == "commander"]
            others = [m for m in members if m["role"] not in ["captain", "commander"]]

            response = f"🌸 **ACN Members in {chat.title}**\n\n"

            if captains:
                response += "⚓ **Captain:**\n"
                for captain in captains:
                    response += f"• {captain['username']} - {captain['rank']} ({captain['points']} pts)\n"
                response += "\n"

            if commanders:
                response += "🎖️ **Commanders:**\n"
                for commander in commanders:
                    response += f"• {commander['username']} - {commander['rank']} ({commander['points']} pts)\n"
                response += "\n"

            if others:
                response += "⭐ **Members:**\n"
                for member in others[:10]:  # Limit to prevent long messages
                    response += f"• {member['username']} - {member['rank']} ({member['points']} pts)\n"

                if len(others) > 10:
                    response += f"... and {len(others) - 10} more members\n"

            await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def award_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Award loyalty points to a member (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 2:
        await msg.reply_text("🌸 Usage: `/award <user_id> <points> [reason]")
        return

    try:
        user_id = int(args[0])
        points = int(args[1])
        reason = " ".join(args[2:]) if len(args) > 2 else "Leadership award"
    except ValueError:
        await msg.reply_text("🌸 Invalid user ID or points format.")
        return

    if points <= 0:
        await msg.reply_text("🌸 Points must be positive.")
        return

    async with async_session_factory() as session:
        async with session.begin():
            # Award points
            loyalty_points = await ACNService.add_loyalty_points(
                session=session,
                user_id=user_id,
                group_id=chat.id,
                points=points,
                activity_type="loyalty",
                action="award",
                metadata=f"Awarded by {update.effective_user.id if update.effective_user else 'Unknown'}: {reason}",
            )

            await msg.reply_text(
                f"🌸 **Points Awarded!**\n\n"
                f"✅ User {user_id} received {points} points\n"
                f"📝 Reason: {reason}\n"
                f"💎 New total: {loyalty_points.points} points\n"
                f"🎯 Current rank: {loyalty_points.rank}"
            )


@admin_captain_commander_only
async def acn_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show ACN information and statistics"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            members = await ACNService.get_group_members(session, chat.id)

            # Calculate statistics
            total_members = len(members)
            total_points = sum(m["points"] for m in members)

            from datetime import datetime

            def get_timestamp(activity):
                if isinstance(activity, datetime):
                    return activity.timestamp()
                return float(activity) if activity else 0

            active_members = len(
                [
                    m
                    for m in members
                    if get_timestamp(m["last_activity"]) > time.time() - 86400 * 7
                ]
            )  # Active in last 7 days

            # Count by role
            captains = len([m for m in members if m["role"] == "captain"])
            commanders = len([m for m in members if m["role"] == "commander"])

            response = f"🌸 **Anime Crew Network - {chat.title}**\n\n"
            response += "📊 **Statistics:**\n"
            response += f"• Total Members: {total_members}\n"
            response += f"• Active Members: {active_members} (last 7 days)\n"
            response += f"• Total Points: {total_points}\n"
            response += f"• Average Points: {total_points // total_members if total_members > 0 else 0}\n\n"

            response += "👥 **Leadership:**\n"
            response += f"• Captain: {captains}\n"
            response += f"• Commanders: {commanders}\n\n"

            response += "🎯 **This bot works exclusively for ACN members only!**"

            await msg.reply_text(response, parse_mode="Markdown")


def register(app) -> None:
    """Register ACN loyalty commands"""
    app.add_handler(CommandHandler("acn_status", acn_status))
    app.add_handler(CommandHandler("loyalty_leaderboard", loyalty_leaderboard))
    app.add_handler(CommandHandler("addacngroup", add_acn_group))
    app.add_handler(CommandHandler("addacn", add_acn_member))
    app.add_handler(CommandHandler("removeacn", remove_acn_member))
    app.add_handler(CommandHandler("acn_members", acn_members))
    app.add_handler(CommandHandler("award", award_points))
    app.add_handler(CommandHandler("acn_info", acn_info))

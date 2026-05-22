"""Profile plugin — /profile and /setbio commands with Nico Robin themed output."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from io import BytesIO

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.database import async_session_factory
from src.bot.services.acn_service import ACNService
from src.bot.services.group_service import GroupService
from src.bot.services.privacy_service import PrivacyService
from src.bot.services.profile_service import ProfileService
from src.bot.services.security_audit_service import SecurityAuditService
from src.bot.services.user_service import UserService
from src.bot.utils.decorators import group_only, sanitize_input
from src.bot.utils.permissions import is_sudo


def _days_between(dt: datetime | None) -> int:
    """Calculate days between a datetime and now."""
    if dt is None:
        return 0
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return max(0, (now - dt).days)


def _format_number(n: int) -> str:
    """Format number with commas: 12847 → 12,847."""
    return f"{n:,}"


def _format_profile_card(data: dict) -> str:
    """Render the full Nico Robin themed profile card."""
    # Identity
    name = f"{data['first_name']} {data['last_name']}".strip()
    username = f"@{data['username']}" if data.get("username") else "—"
    acn_role = data.get("acn_role", "Crew Member")
    user_id = data["user_id"]

    # Dates
    join_date = data.get("join_date") or data.get("first_seen_at")
    join_str = join_date.strftime("%Y-%m-%d") if join_date else "Unknown"
    account_age = _days_between(join_date)

    # Activity
    total_msgs = data.get("total_messages", 0)
    avg_per_day = round(total_msgs / max(1, account_age), 1)
    streak = data.get("streak_days", 0)
    peak_hour = ProfileService.format_peak_hour(data.get("peak_hour", 0))
    active_days = data.get("active_days", 0)
    activity_bar = ProfileService.build_activity_bar(active_days, account_age)

    # Media breakdown
    stickers = data.get("stickers_sent", 0)
    photos = data.get("photos_sent", 0)
    videos = data.get("videos_sent", 0)
    voice = data.get("voice_sent", 0)
    commands = data.get("commands_used", 0)

    # Crew status
    reputation = data.get("reputation", 0)
    rep_sign = "+" if reputation >= 0 else ""
    loyalty_rank = data.get("loyalty_rank", "Recruit")
    points = data.get("points", 0)
    level = data.get("level", 1)
    lb_pos = data.get("leaderboard_pos", "—")

    # Record
    active_warns = data.get("active_warns", 0)
    ban_count = data.get("ban_count", 0)
    swear_v = data.get("swear_violations", 0)
    security_score = ProfileService.calculate_security_score(data)

    # Security score emoji
    if security_score >= 90:
        sec_emoji = "🟢"
    elif security_score >= 70:
        sec_emoji = "🟡"
    elif security_score >= 50:
        sec_emoji = "🟠"
    else:
        sec_emoji = "🔴"

    # Bio
    bio = data.get("bio") or "No bio set. Use /setbio to add one."
    profile_views = data.get("profile_views", 0)

    # Admin badge
    admin_badge = " 👑" if data.get("is_admin") else ""

    card = (
        f"📖 ━━━━ PONEGLYPH RECORD ━━━━ 📖\n"
        f"\n"
        f"🌸 Nico Robin's Archive\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"👤 Name: {name}{admin_badge}\n"
        f"🆔 ID: {user_id}\n"
        f"📛 Username: {username}\n"
        f"🏴‍☠️ ACN Role: {acn_role}\n"
        f"📅 First Seen: {join_str}\n"
        f"⏳ Account Age: {account_age} days\n"
        f"\n"
        f"📊 ━━━ ACTIVITY LOG ━━━ 📊\n"
        f"\n"
        f"💬 Messages: {_format_number(total_msgs)}\n"
        f"📝 Avg/Day: {avg_per_day}\n"
        f"🔥 Streak: {streak} days\n"
        f"📈 Peak Hour: {peak_hour}\n"
        f"🗓️ Active Days: {active_days}/{account_age}\n"
        f"📊 Activity: {activity_bar}\n"
        f"\n"
        f"🎭 ━━━ MEDIA MIX ━━━ 🎭\n"
        f"\n"
        f"🖼️ Photos: {_format_number(photos)}  "
        f"🎬 Videos: {_format_number(videos)}\n"
        f"🌸 Stickers: {_format_number(stickers)}  "
        f"🎙️ Voice: {_format_number(voice)}\n"
        f"⚡ Commands: {_format_number(commands)}\n"
        f"\n"
        f"🏅 ━━━ CREW STATUS ━━━ 🏅\n"
        f"\n"
        f"⭐ Reputation: {rep_sign}{reputation}\n"
        f"🎖️ Loyalty Rank: {loyalty_rank}\n"
        f"💎 Points: {_format_number(points)}\n"
        f"📈 Level: {level}\n"
        f"🏆 Leaderboard: #{lb_pos}\n"
        f"\n"
        f"⚠️ ━━━ RECORD SCROLL ━━━ ⚠️\n"
        f"\n"
        f"🔶 Warnings: {active_warns}\n"
        f"🔴 Bans: {ban_count}\n"
        f"🚫 Swear Violations: {swear_v}\n"
        f"{sec_emoji} Security Score: {security_score}/100\n"
        f"\n"
        f"🌺 ━━━ ABOUT ME ━━━ 🌺\n"
        f"\n"
        f"「{bio}」\n"
        f"\n"
        f"👁️ Profile Views: {profile_views}\n"
        f"📖 Record verified by Nico Robin 🌸\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return card


@group_only
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a member's full profile card.

    Usage:
      /profile — View your own profile
      /profile @username — View another member's profile
      Reply to a message with /profile — View that member's profile
    """
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    # Determine target user
    target = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user
    elif context.args:
        # Try to find user by username
        arg = context.args[0].lstrip("@")
        async with async_session_factory() as session:
            user_obj = await UserService.find_by_username(session, arg)
            if user_obj:
                # Build profile for this user
                async with async_session_factory() as s2:
                    data = await ProfileService.build_full_profile(
                        s2, user_obj.user_id, chat.id
                    )
                card = _format_profile_card(data)
                await msg.reply_text(card)
                return
            else:
                await msg.reply_text("🌸 That nakama isn't in my records.")
                return
    else:
        target = update.effective_user

    if target is None:
        return

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await UserService.ensure_user(session, target)
        data = await ProfileService.build_full_profile(session, target.id, chat.id)
        # Override with live Telegram data for freshness
        data["first_name"] = target.first_name or data["first_name"]
        data["last_name"] = target.last_name or ""
        data["username"] = target.username or data.get("username")

    card = _format_profile_card(data)
    await msg.reply_text(card)


@group_only
@sanitize_input
async def setbio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set your personal bio for the profile card.

    Usage: /setbio <text> (max 200 characters)
    """
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return

    if not context.args:
        await msg.reply_text(
            "🌸 Usage: `/setbio <your bio text>`\n"
            "Max 200 characters. Express yourself!\n\n"
            "Example: `/setbio Kaizoku ou ni ore wa naru!`"
        )
        return

    bio_text = " ".join(context.args)[:200]

    async with async_session_factory() as session:
        async with session.begin():
            await GroupService.ensure_group(session, chat)
            await UserService.ensure_user(session, user)
            await ProfileService.set_bio(session, user.id, chat.id, bio_text)

    await msg.reply_text(
        f"🌸 Bio updated!\n\n「{bio_text}」\n\n📖 Your poneglyph has been inscribed."
    )


@group_only
async def export_my_data_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    async with async_session_factory() as session:
        export = await PrivacyService.export_user_data(session, user.id)

    payload = json.dumps(export, indent=2, ensure_ascii=True)
    document = BytesIO(payload.encode("utf-8"))
    document.name = f"nico_robin_data_export_{user.id}.json"
    await msg.reply_document(
        document=document,
        filename=document.name,
        caption="🌸 I gathered the pages of your archive into one export.",
    )


@group_only
async def delete_my_data_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    if not context.args or context.args[0].lower() != "confirm":
        await msg.reply_text(
            "🌸 This will clear your saved profile, warnings, points, flirting stats, and notes you created.\n"
            "Use `/delete_my_data confirm` when you are certain."
        )
        return

    async with async_session_factory() as session:
        async with session.begin():
            counts = await PrivacyService.soft_delete_user_data(session, user.id)
            await SecurityAuditService.log_event(
                session=session,
                event_type="delete_my_data",
                severity="MEDIUM",
                user_id=user.id,
                group_id=chat.id,
                reason="User requested personal data deletion",
                details=counts,
            )

    await msg.reply_text(
        "🌸 Your personal archive has been cleared from the records I manage."
    )


@group_only
async def clear_user_data_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    if not (is_sudo(user.id) or await ACNService.is_captain(user.id)):
        await msg.reply_text("🌸 Only the captain may order another archive erased.")
        return

    if len(context.args) < 2 or context.args[1].lower() != "confirm":
        await msg.reply_text(
            "🌸 Usage: `/clear_user_data <user_id> confirm`\n"
            "I need the full command as a deliberate choice."
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await msg.reply_text("🌸 Give me a valid numeric user id.")
        return

    async with async_session_factory() as session:
        async with session.begin():
            counts = await PrivacyService.soft_delete_user_data(session, target_user_id)
            await SecurityAuditService.log_event(
                session=session,
                event_type="clear_user_data",
                severity="HIGH",
                user_id=user.id,
                target_id=target_user_id,
                group_id=chat.id,
                reason="Captain-initiated user data deletion",
                details=counts,
            )

    await msg.reply_text(
        f"🌸 The archive for `{target_user_id}` has been cleared from my records.",
        parse_mode="Markdown",
    )


def register(app) -> None:
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("setbio", setbio_command))
    app.add_handler(CommandHandler("export_my_data", export_my_data_command))
    app.add_handler(CommandHandler("delete_my_data", delete_my_data_command))
    app.add_handler(CommandHandler("clear_user_data", clear_user_data_command))

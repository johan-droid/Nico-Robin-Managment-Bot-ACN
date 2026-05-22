"""ProfileService — aggregates data from 8+ tables into a single profile view."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.models.audit import ActionLog
from src.bot.models.loyalty import ACNWhitelist, LoyaltyPoints
from src.bot.models.points import UserPoints
from src.bot.models.profile import MemberProfile
from src.bot.models.swear_word import SwearViolation
from src.bot.models.user import GroupMember, User
from src.bot.models.warn import Warn
from src.bot.services.crypto_service import get_crypto_service


class ProfileService:
    """Aggregates profile data from all tables."""

    @staticmethod
    async def get_or_create(
        session: AsyncSession, user_id: int, group_id: int
    ) -> MemberProfile:
        """Get or create a MemberProfile row."""
        result = await session.execute(
            select(MemberProfile).where(
                MemberProfile.user_id == user_id,
                MemberProfile.group_id == group_id,
                MemberProfile.deleted_at.is_(None),
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = MemberProfile(
                user_id=user_id,
                group_id=group_id,
                hourly_activity={},
            )
            session.add(profile)
            await session.flush()
        return profile

    @staticmethod
    async def increment_stats(
        session: AsyncSession,
        user_id: int,
        group_id: int,
        *,
        messages: int = 0,
        stickers: int = 0,
        photos: int = 0,
        videos: int = 0,
        voice: int = 0,
        documents: int = 0,
        commands: int = 0,
        hourly: dict | None = None,
        new_days: int = 0,
    ) -> None:
        """Increment profile stats (called by message_tracker flush)."""
        profile = await ProfileService.get_or_create(session, user_id, group_id)

        profile.total_messages += messages
        profile.stickers_sent += stickers
        profile.photos_sent += photos
        profile.videos_sent += videos
        profile.voice_sent += voice
        profile.documents_sent += documents
        profile.commands_used += commands
        profile.active_days += new_days
        profile.last_message_at = datetime.now(UTC)

        # Merge hourly activity
        if hourly:
            existing = profile.hourly_activity or {}
            for hour, count in hourly.items():
                existing[hour] = existing.get(hour, 0) + count
            profile.hourly_activity = existing

            # Recalculate peak hour
            if existing:
                profile.peak_hour = int(max(existing, key=lambda h: existing[h]))

        await session.flush()

    @staticmethod
    async def set_bio(
        session: AsyncSession, user_id: int, group_id: int, bio: str
    ) -> MemberProfile:
        """Set user bio text."""
        profile = await ProfileService.get_or_create(session, user_id, group_id)
        profile.bio = get_crypto_service().encrypt_text(bio[:200])  # Hard cap
        await session.flush()
        return profile

    @staticmethod
    async def build_full_profile(
        session: AsyncSession, user_id: int, group_id: int
    ) -> dict:
        """Aggregate ALL data for a user from every table into a profile dict."""
        data: dict = {}

        # ── Core user info ──
        user_result = await session.execute(
            select(User).where(User.user_id == user_id, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if user:
            data["first_name"] = user.first_name or "Unknown"
            data["last_name"] = user.last_name or ""
            data["username"] = user.username
            data["reputation"] = user.reputation
            data["ban_count"] = user.ban_count
            data["warn_count_global"] = user.warn_count
            data["is_bot"] = user.is_bot
            data["join_date"] = user.join_date
        else:
            data["first_name"] = "Unknown"
            data["last_name"] = ""
            data["username"] = None
            data["reputation"] = 0
            data["ban_count"] = 0
            data["warn_count_global"] = 0
            data["is_bot"] = False
            data["join_date"] = None

        data["user_id"] = user_id

        # ── Group membership ──
        gm_result = await session.execute(
            select(GroupMember).where(
                GroupMember.user_id == user_id,
                GroupMember.group_id == group_id,
            )
        )
        gm = gm_result.scalar_one_or_none()
        data["group_joined_at"] = gm.joined_at if gm else None
        data["is_admin"] = gm.is_admin if gm else False

        # ── MemberProfile ──
        profile = await ProfileService.get_or_create(session, user_id, group_id)
        profile.profile_views += 1
        data["total_messages"] = profile.total_messages
        data["stickers_sent"] = profile.stickers_sent
        data["photos_sent"] = profile.photos_sent
        data["videos_sent"] = profile.videos_sent
        data["voice_sent"] = profile.voice_sent
        data["documents_sent"] = profile.documents_sent
        data["commands_used"] = profile.commands_used
        data["replies_sent"] = profile.replies_sent
        data["bio"] = get_crypto_service().decrypt_text(profile.bio)
        data["peak_hour"] = profile.peak_hour
        data["active_days"] = profile.active_days
        data["last_message_at"] = profile.last_message_at
        data["profile_views"] = profile.profile_views
        data["first_seen_at"] = profile.first_seen_at
        data["hourly_activity"] = profile.hourly_activity or {}

        # ── Active warnings ──
        warn_result = await session.execute(
            select(func.count(Warn.warn_id)).where(
                Warn.user_id == user_id,
                Warn.group_id == group_id,
                Warn.is_active == True,  # noqa: E712
                Warn.deleted_at.is_(None),
            )
        )
        data["active_warns"] = warn_result.scalar() or 0

        # ── Swear violations ──
        sv_result = await session.execute(
            select(func.count(SwearViolation.violation_id)).where(
                SwearViolation.user_id == user_id,
                SwearViolation.group_id == group_id,
            )
        )
        data["swear_violations"] = sv_result.scalar() or 0

        # ── Loyalty points ──
        lp_result = await session.execute(
            select(LoyaltyPoints).where(
                LoyaltyPoints.user_id == user_id,
                LoyaltyPoints.group_id == group_id,
                LoyaltyPoints.deleted_at.is_(None),
            )
        )
        lp = lp_result.scalar_one_or_none()
        data["loyalty_points"] = lp.points if lp else 0
        data["loyalty_rank"] = lp.rank if lp else "Recruit"

        # ── Points system ──
        up_result = await session.execute(
            select(UserPoints).where(
                UserPoints.user_id == user_id,
                UserPoints.group_id == group_id,
                UserPoints.deleted_at.is_(None),
            )
        )
        up = up_result.scalar_one_or_none()
        data["points"] = up.current_points if up else 0
        data["level"] = up.level if up else 1
        data["experience"] = up.experience if up else 0
        data["streak_days"] = up.streak_days if up else 0

        # ── ACN role ──
        acn_result = await session.execute(
            select(ACNWhitelist).where(
                ACNWhitelist.entity_id == user_id,
                ACNWhitelist.whitelist_type == "user",
                ACNWhitelist.is_active == True,  # noqa: E712
            )
        )
        acn = acn_result.scalar_one_or_none()
        data["acn_role"] = acn.role.title() if acn else "Crew Member"

        # ── Moderation actions received ──
        mod_result = await session.execute(
            select(func.count(ActionLog.log_id)).where(
                ActionLog.target_id == user_id,
                ActionLog.group_id == group_id,
            )
        )
        data["mod_actions"] = mod_result.scalar() or 0

        # ── Leaderboard position ──
        if up:
            rank_result = await session.execute(
                select(func.count(UserPoints.points_id)).where(
                    UserPoints.group_id == group_id,
                    UserPoints.current_points > up.current_points,
                    UserPoints.deleted_at.is_(None),
                )
            )
            data["leaderboard_pos"] = (rank_result.scalar() or 0) + 1
        else:
            data["leaderboard_pos"] = "—"

        await session.flush()
        return data

    @staticmethod
    def calculate_security_score(data: dict) -> int:
        """Calculate a 0-100 security score based on moderation history."""
        score = 100
        score -= data.get("active_warns", 0) * 15
        score -= data.get("ban_count", 0) * 25
        score -= data.get("swear_violations", 0) * 5
        score -= data.get("mod_actions", 0) * 2
        return max(0, min(100, score))

    @staticmethod
    def build_activity_bar(active_days: int, total_days: int, width: int = 10) -> str:
        """Generate ██████░░░░ activity bar."""
        if total_days <= 0:
            ratio = 0.0
        else:
            ratio = min(1.0, active_days / total_days)
        filled = round(ratio * width)
        empty = width - filled
        pct = round(ratio * 100)
        return f"{'█' * filled}{'░' * empty} {pct}%"

    @staticmethod
    def format_peak_hour(hour: int) -> str:
        """Format 24h hour as 12h with AM/PM."""
        if hour == 0:
            return "12 AM"
        elif hour < 12:
            return f"{hour} AM"
        elif hour == 12:
            return "12 PM"
        else:
            return f"{hour - 12} PM"

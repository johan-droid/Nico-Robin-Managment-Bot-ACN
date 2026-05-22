from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.models.flirting import FlirtingStats
from src.bot.models.loyalty import LoyaltyPoints
from src.bot.models.note import Note
from src.bot.models.points import UserPoints
from src.bot.models.profile import MemberProfile
from src.bot.models.user import User
from src.bot.models.warn import Warn
from src.bot.services.crypto_service import get_crypto_service
from src.bot.services.note_service import NoteService


class PrivacyService:
    @staticmethod
    async def export_user_data(
        session: AsyncSession,
        user_id: int,
    ) -> dict[str, object]:
        crypto = get_crypto_service()
        export: dict[str, object] = {
            "generated_at": datetime.now(UTC).isoformat(),
            "user_id": user_id,
        }

        user = await session.get(User, user_id)
        export["user"] = {
            "user_id": user.user_id if user else user_id,
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
            "last_name": user.last_name if user else None,
            "reputation": user.reputation if user else 0,
            "ban_count": user.ban_count if user else 0,
            "warn_count": user.warn_count if user else 0,
            "deleted_at": (
                user.deleted_at.isoformat() if user and user.deleted_at else None
            ),
        }

        profiles = (
            (
                await session.execute(
                    select(MemberProfile).where(MemberProfile.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        export["profiles"] = [
            {
                "group_id": profile.group_id,
                "bio": crypto.decrypt_text(profile.bio),
                "total_messages": profile.total_messages,
                "commands_used": profile.commands_used,
                "first_seen_at": (
                    profile.first_seen_at.isoformat() if profile.first_seen_at else None
                ),
                "deleted_at": (
                    profile.deleted_at.isoformat() if profile.deleted_at else None
                ),
            }
            for profile in profiles
        ]

        warns = (
            (await session.execute(select(Warn).where(Warn.user_id == user_id)))
            .scalars()
            .all()
        )
        export["warns"] = [
            {
                "warn_id": warn.warn_id,
                "group_id": warn.group_id,
                "admin_id": warn.admin_id,
                "reason": crypto.decrypt_text(warn.reason),
                "issued_at": warn.issued_at.isoformat() if warn.issued_at else None,
                "expires_at": warn.expires_at.isoformat() if warn.expires_at else None,
                "is_active": warn.is_active,
                "deleted_at": warn.deleted_at.isoformat() if warn.deleted_at else None,
            }
            for warn in warns
        ]

        notes = (
            (await session.execute(select(Note).where(Note.created_by == user_id)))
            .scalars()
            .all()
        )
        export["notes"] = [
            {
                "note_id": note.note_id,
                "group_id": note.group_id,
                "name": note.name,
                "content": crypto.decrypt_text(note.content),
                "deleted_at": note.deleted_at.isoformat() if note.deleted_at else None,
            }
            for note in notes
            if NoteService.validate_note_name(note.name)
        ]

        loyalty = (
            (
                await session.execute(
                    select(LoyaltyPoints).where(LoyaltyPoints.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        export["loyalty_points"] = [
            {
                "group_id": item.group_id,
                "points": item.points,
                "rank": item.rank,
                "total_actions": item.total_actions,
                "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
            }
            for item in loyalty
        ]

        point_accounts = (
            (
                await session.execute(
                    select(UserPoints).where(UserPoints.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        export["point_accounts"] = [
            {
                "group_id": item.group_id,
                "current_points": item.current_points,
                "total_earned": item.total_earned,
                "total_spent": item.total_spent,
                "level": item.level,
                "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
            }
            for item in point_accounts
        ]

        flirting_stats = (
            (
                await session.execute(
                    select(FlirtingStats).where(FlirtingStats.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        export["flirting_stats"] = [
            {
                "group_id": item.group_id,
                "total_attempts": item.total_attempts,
                "successful_flirts": item.successful_flirts,
                "points_earned": item.points_earned,
                "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
            }
            for item in flirting_stats
        ]

        return export

    @staticmethod
    async def soft_delete_user_data(
        session: AsyncSession,
        user_id: int,
    ) -> dict[str, int]:
        now = datetime.now(UTC)
        crypto = get_crypto_service()
        counts = {
            "profiles": 0,
            "warns": 0,
            "notes": 0,
            "loyalty_points": 0,
            "point_accounts": 0,
            "flirting_stats": 0,
        }

        profiles = (
            (
                await session.execute(
                    select(MemberProfile).where(
                        MemberProfile.user_id == user_id,
                        MemberProfile.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for profile in profiles:
            profile.bio = None
            profile.deleted_at = now
            counts["profiles"] += 1

        warns = (
            (
                await session.execute(
                    select(Warn).where(
                        Warn.user_id == user_id, Warn.deleted_at.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        for warn in warns:
            warn.reason = crypto.encrypt_text("Deleted at user request")
            warn.is_active = False
            warn.deleted_at = now
            counts["warns"] += 1

        notes = (
            (
                await session.execute(
                    select(Note).where(
                        Note.created_by == user_id, Note.deleted_at.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        for note in notes:
            note.content = crypto.encrypt_text("[deleted at user request]")
            note.deleted_at = now
            counts["notes"] += 1

        loyalty_rows = (
            (
                await session.execute(
                    select(LoyaltyPoints).where(
                        LoyaltyPoints.user_id == user_id,
                        LoyaltyPoints.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in loyalty_rows:
            row.deleted_at = now
            counts["loyalty_points"] += 1

        point_rows = (
            (
                await session.execute(
                    select(UserPoints).where(
                        UserPoints.user_id == user_id,
                        UserPoints.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in point_rows:
            row.deleted_at = now
            counts["point_accounts"] += 1

        flirting_rows = (
            (
                await session.execute(
                    select(FlirtingStats).where(
                        FlirtingStats.user_id == user_id,
                        FlirtingStats.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in flirting_rows:
            row.deleted_at = now
            counts["flirting_stats"] += 1

        user = await session.get(User, user_id)
        if user is not None:
            user.username = None
            user.first_name = "Deleted"
            user.last_name = "User"
            user.deleted_at = now

        return counts

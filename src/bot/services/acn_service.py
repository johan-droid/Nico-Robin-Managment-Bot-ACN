from __future__ import annotations

import time
from functools import wraps

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Chat
from telegram.ext import ContextTypes

from src.bot.bot.middleware.rate_limiter import get_redis
from src.bot.config import settings
from src.bot.database import async_session_factory
from src.bot.models.loyalty import ACNWhitelist, LoyaltyPoints
from src.bot.utils.permissions import is_telegram_admin


class ACNService:
    """Anime Crew Network validation and loyalty service"""

    # Captain and commander IDs loaded from environment
    CAPTAIN_ID = settings.captain_id
    COMMANDER_IDS = set(settings.commander_ids)
    ROLE_CACHE_TTL = 300

    @staticmethod
    def _role_cache_key(user_id: int) -> str:
        return f"acn:role:{user_id}"

    @staticmethod
    async def _cache_role(user_id: int, role: str) -> None:
        try:
            await get_redis().set(
                ACNService._role_cache_key(user_id),
                role,
                ex=ACNService.ROLE_CACHE_TTL,
            )
        except Exception:
            return

    @staticmethod
    async def invalidate_role_cache(user_id: int) -> None:
        try:
            await get_redis().delete(ACNService._role_cache_key(user_id))
        except Exception:
            return

    @staticmethod
    async def is_acn_group(group_id: int) -> bool:
        """Check if group is whitelisted for ACN"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.entity_id == group_id,
                    ACNWhitelist.whitelist_type == "group",
                    ACNWhitelist.is_active,
                )
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    async def is_acn_member(user_id: int) -> bool:
        """Check if user is whitelisted ACN member"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.entity_id == user_id,
                    ACNWhitelist.whitelist_type == "user",
                    ACNWhitelist.is_active,
                )
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_user_role(user_id: int) -> str:
        """Get user's ACN role"""
        try:
            cached_role = await get_redis().get(ACNService._role_cache_key(user_id))
            if cached_role:
                return str(cached_role)
        except Exception:
            pass

        if user_id == ACNService.CAPTAIN_ID:
            await ACNService._cache_role(user_id, "captain")
            return "captain"

        if user_id in ACNService.COMMANDER_IDS:
            await ACNService._cache_role(user_id, "commander")
            return "commander"

        # Check database for role
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.entity_id == user_id,
                    ACNWhitelist.whitelist_type == "user",
                    ACNWhitelist.is_active,
                )
            )
            whitelist_entry = result.scalar_one_or_none()
            if whitelist_entry and whitelist_entry.role:
                normalized_role = whitelist_entry.role.strip().lower()
                await ACNService._cache_role(user_id, normalized_role)
                return normalized_role
        await ACNService._cache_role(user_id, "none")
        return "none"

    @staticmethod
    async def is_captain(user_id: int) -> bool:
        """Check if user is the captain (Monkey D. Sparrow)"""
        if user_id == ACNService.CAPTAIN_ID:
            return True
        return await ACNService.get_user_role(user_id) == "captain"

    @staticmethod
    async def is_commander(user_id: int) -> bool:
        """Check if user is a commander"""
        return user_id in ACNService.COMMANDER_IDS

    @staticmethod
    async def is_admin_or_owner(
        user_id: int, chat: Chat, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Check if user is admin, owner, captain, or commander"""
        # Check captain/commander status first (highest priority)
        if await ACNService.is_captain(user_id) or await ACNService.is_commander(
            user_id
        ):
            return True

        # Check Telegram admin/owner status
        try:
            return await is_telegram_admin(context, chat.id, user_id)
        except Exception:
            return False

    @staticmethod
    async def validate_group_access(chat: Chat, user_id: int) -> tuple[bool, str]:
        """Validate if user can access bot in this group"""
        if chat.type == "private":
            return True, "Private chat"

        # Check if group is ACN whitelisted
        if not await ACNService.is_acn_group(chat.id):
            return False, "This bot only works in Anime Crew Network groups."

        # Check if user is ACN member
        if not await ACNService.is_acn_member(user_id):
            return False, "Only ACN members can use this bot."

        return True, "Access granted"

    @staticmethod
    async def add_to_whitelist(
        session: AsyncSession,
        entity_id: int,
        entity_name: str,
        whitelist_type: str,
        role: str,
        added_by: int | None = None,
        notes: str | None = None,
    ) -> ACNWhitelist:
        """Add entity to ACN whitelist"""
        whitelist = ACNWhitelist(
            entity_id=entity_id,
            entity_name=entity_name,
            whitelist_type=whitelist_type,
            role=role,
            added_by=added_by,
            notes=notes,
        )
        session.add(whitelist)
        await session.flush()
        if whitelist_type == "user":
            await ACNService.invalidate_role_cache(entity_id)
        return whitelist

    @staticmethod
    async def remove_from_whitelist(
        session: AsyncSession, entity_id: int, whitelist_type: str
    ) -> bool:
        """Remove entity from ACN whitelist"""
        result = await session.execute(
            select(ACNWhitelist).where(
                ACNWhitelist.entity_id == entity_id,
                ACNWhitelist.whitelist_type == whitelist_type,
            )
        )
        whitelist_entry = result.scalar_one_or_none()
        if whitelist_entry:
            await session.delete(whitelist_entry)
            if whitelist_type == "user":
                await ACNService.invalidate_role_cache(entity_id)
            return True
        return False

    @staticmethod
    async def get_loyalty_points(
        session: AsyncSession, user_id: int, group_id: int
    ) -> LoyaltyPoints | None:
        """Get user's loyalty points for a group"""
        result = await session.execute(
            select(LoyaltyPoints).where(
                LoyaltyPoints.user_id == user_id, LoyaltyPoints.group_id == group_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add_loyalty_points(
        session: AsyncSession,
        user_id: int,
        group_id: int,
        points: int,
        activity_type: str,
        action: str,
        metadata: str | None = None,
    ) -> LoyaltyPoints:
        """Add loyalty points to user"""
        # Get or create loyalty points record
        loyalty_points = await ACNService.get_loyalty_points(session, user_id, group_id)
        if not loyalty_points:
            loyalty_points = LoyaltyPoints(
                user_id=user_id,
                group_id=group_id,
                points=0,
                total_actions=0,
                last_activity=int(time.time()),
            )
            session.add(loyalty_points)

        # Update points and stats
        loyalty_points.points += points
        loyalty_points.total_actions += 1
        loyalty_points.last_activity = int(time.time())

        # Update rank based on points
        loyalty_points.rank = ACNService.get_rank_for_points(loyalty_points.points)

        # Record activity
        from models.loyalty import ACNActivity

        activity = ACNActivity(
            user_id=user_id,
            group_id=group_id,
            activity_type=activity_type,
            action=action,
            points_earned=points,
            extra_data=metadata,
        )
        session.add(activity)

        await session.flush()
        return loyalty_points

    @staticmethod
    def get_rank_for_points(points: int) -> str:
        """Get rank based on loyalty points"""
        if points >= 10000:
            return "Fleet Admiral"
        elif points >= 5000:
            return "Vice Admiral"
        elif points >= 2000:
            return "Rear Admiral"
        elif points >= 1000:
            return "Commodore"
        elif points >= 500:
            return "Captain"
        elif points >= 200:
            return "Commander"
        elif points >= 100:
            return "Lieutenant"
        elif points >= 50:
            return "Ensign"
        else:
            return "Crew Member"

    @staticmethod
    async def get_group_members(session: AsyncSession, group_id: int) -> list[dict]:
        """Get all ACN members in a group with their roles"""
        result = await session.execute(
            select(ACNWhitelist, LoyaltyPoints)
            .join(
                LoyaltyPoints,
                (ACNWhitelist.entity_id == LoyaltyPoints.user_id)
                & (ACNWhitelist.whitelist_type == "user")
                & (LoyaltyPoints.group_id == group_id),
                isouter=True,
            )
            .where(ACNWhitelist.whitelist_type == "user", ACNWhitelist.is_active)
        )

        members = []
        for whitelist_entry, loyalty_points in result:
            member_data = {
                "user_id": whitelist_entry.entity_id,
                "username": whitelist_entry.entity_name,
                "role": whitelist_entry.role,
                "points": loyalty_points.points if loyalty_points else 0,
                "rank": loyalty_points.rank if loyalty_points else "Crew Member",
                "last_activity": loyalty_points.last_activity if loyalty_points else 0,
            }
            members.append(member_data)

        return members


# Decorator for ACN-only commands
def acn_only(func):
    """Decorator to ensure command only works in ACN groups for ACN members"""

    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        chat = update.effective_chat
        user = update.effective_user

        if not chat or not user:
            return

        # Validate group access
        can_access, message = await ACNService.validate_group_access(chat, user.id)
        if not can_access:
            if update.message:
                await update.message.reply_text(f"🚫 {message}")
            return

        # Execute the original function
        return await func(update, context, *args, **kwargs)

    return wrapper


# Decorator for captain/commander only commands
def captain_commander_only(func):
    """Decorator to ensure only captain or commanders can use command"""

    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        chat = update.effective_chat
        user = update.effective_user

        if not user or not chat:
            return

        # Allow captains, commanders, and Telegram admins/owners
        if not await ACNService.is_admin_or_owner(user.id, chat, context):
            if update.message:
                await update.message.reply_text(
                    "🚫 Only admins, owners, Monkey D. Sparrow, and commanders can use this command."
                )
            return

        # Execute the original function
        return await func(update, context, *args, **kwargs)

    return wrapper


# Decorator for admin/captain/commander only commands
def admin_captain_commander_only(func):
    """Decorator to ensure only admins, captain, or commanders can use command"""

    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        chat = update.effective_chat
        user = update.effective_user

        if not chat or not user:
            return

        # Check if captain or commander (bypass admin check)
        if await ACNService.is_captain(user.id) or await ACNService.is_commander(
            user.id
        ):
            return await func(update, context, *args, **kwargs)

        # Check admin status
        try:
            from src.bot.utils.permissions import is_telegram_admin

            if not await is_telegram_admin(context, chat.id, user.id):
                if update.message:
                    await update.message.reply_text(
                        "🚫 Only admins, Monkey D. Sparrow, and commanders can use this command."
                    )
                return
        except Exception:
            if update.message:
                await update.message.reply_text("🚫 Permission check failed.")
            return

        # Execute the original function
        return await func(update, context, *args, **kwargs)

    return wrapper

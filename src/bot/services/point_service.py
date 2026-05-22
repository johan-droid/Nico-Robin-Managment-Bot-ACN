from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.database import async_session_factory
from src.bot.models.points import (
    Apploid,
    PointTransaction,
    UserApploid,
    UserPoints,
)


class PointService:
    """Comprehensive point system with custom apploids"""

    # Point earning activities and their rewards
    EARNING_ACTIVITIES = {
        "message": {"points": 1, "description": "Sending messages", "cooldown": 60},
        "flirt_success": {
            "points": 5,
            "description": "Successful flirting",
            "cooldown": 300,
        },
        "bond_interaction": {
            "points": 3,
            "description": "Bot friendship interaction",
            "cooldown": 600,
        },
        "daily_streak": {
            "points": 10,
            "description": "Daily activity streak",
            "cooldown": 86400,
        },
        "weekly_streak": {
            "points": 50,
            "description": "Weekly activity streak",
            "cooldown": 604800,
        },
        "achievement": {
            "points": 20,
            "description": "Earning achievements",
            "cooldown": 0,
        },
        "bonus": {"points": 15, "description": "Special bonuses", "cooldown": 0},
        "helpful": {
            "points": 8,
            "description": "Helpful contributions",
            "cooldown": 3600,
        },
        "creative": {"points": 12, "description": "Creative content", "cooldown": 7200},
        "social": {"points": 6, "description": "Social interactions", "cooldown": 1800},
    }

    # Level requirements and benefits
    LEVEL_REQUIREMENTS = {
        1: {"name": "Novice Scholar", "points": 0, "bonus": 1.0},
        2: {"name": "Apprentice Archaeologist", "points": 100, "bonus": 1.1},
        3: {"name": "Journeyman Historian", "points": 250, "bonus": 1.2},
        4: {"name": "Expert Researcher", "points": 500, "bonus": 1.3},
        5: {"name": "Master Scholar", "points": 1000, "bonus": 1.4},
        6: {"name": "Senior Archaeologist", "points": 2000, "bonus": 1.5},
        7: {"name": "Lead Historian", "points": 5000, "bonus": 1.6},
        8: {"name": "Chief Researcher", "points": 10000, "bonus": 1.8},
        9: {"name": "Master Archaeologist", "points": 25000, "bonus": 2.0},
        10: {"name": "Legendary Scholar", "points": 50000, "bonus": 2.5},
    }

    # Nico Robin themed apploids
    DEFAULT_APPLOIDS = [
        {
            "name": "Robin Classic",
            "emoji": "🌸",
            "description": "Classic Nico Robin with gentle smile",
            "rarity": "common",
            "required_level": 1,
            "required_points": 0,
        },
        {
            "name": "Scholar Robin",
            "emoji": "📚",
            "description": "Robin with her glasses and books",
            "rarity": "common",
            "required_level": 1,
            "required_points": 50,
        },
        {
            "name": "Devil Child",
            "emoji": "😈",
            "description": "Robin's infamous Devil Child persona",
            "rarity": "rare",
            "required_level": 3,
            "required_points": 500,
        },
        {
            "name": " archaeologist Robin",
            "emoji": "🗺️",
            "description": "Robin with ancient map and tools",
            "rarity": "rare",
            "required_level": 2,
            "required_points": 300,
        },
        {
            "name": "Blossom Robin",
            "emoji": "🌺",
            "description": "Robin surrounded by cherry blossoms",
            "rarity": "epic",
            "required_level": 5,
            "required_points": 2000,
        },
        {
            "name": "Ocean Robin",
            "emoji": "🌊",
            "description": "Robin by the sea with the Thousand Sunny",
            "rarity": "epic",
            "required_level": 4,
            "required_points": 1500,
        },
        {
            "name": "Nightingale Robin",
            "emoji": "🎶",
            "description": "Robin singing softly under the moon",
            "rarity": "epic",
            "required_level": 6,
            "required_points": 3500,
        },
        {
            "name": "Golden Robin",
            "emoji": "⭐",
            "description": "Robin glowing with golden light",
            "rarity": "legendary",
            "required_level": 8,
            "required_points": 10000,
        },
        {
            "name": "Poneglyph Robin",
            "emoji": "📜",
            "description": "Robin decoding ancient poneglyphs",
            "rarity": "legendary",
            "required_level": 7,
            "required_points": 8000,
        },
        {
            "name": "Angel Robin",
            "emoji": "👼",
            "description": "Robin with angelic wings and halo",
            "rarity": "legendary",
            "required_level": 10,
            "required_points": 25000,
        },
    ]

    def __init__(self):
        self.cooldowns = {}  # User cooldowns for activities

    async def initialize_user_points(self, user_id: int, group_id: int) -> UserPoints:
        """Initialize user points if not exists"""

        async with async_session_factory() as session:
            async with session.begin():
                # Check if user points already exist
                result = await session.execute(
                    select(UserPoints).where(
                        UserPoints.user_id == user_id,
                        UserPoints.group_id == group_id,
                    )
                )
                user_points = result.scalar_one_or_none()

                if user_points and user_points.deleted_at is not None:
                    user_points.deleted_at = None
                    return user_points

                if not user_points:
                    # Create new user points
                    user_points = UserPoints(
                        user_id=user_id,
                        group_id=group_id,
                        current_points=0,
                        total_earned=0,
                        total_spent=0,
                        level=1,
                        experience=0,
                        streak_days=0,
                        last_activity=int(time.time()),
                        selected_apploid="Robin Classic",
                    )
                    session.add(user_points)

                    # Give starting bonus
                    await self._award_points(
                        session,
                        user_id,
                        group_id,
                        50,
                        "bonus",
                        "Welcome bonus for joining ACN point system!",
                    )

                    await session.flush()

                return user_points

    async def award_points(
        self,
        session: AsyncSession,
        user_id: int,
        group_id: int,
        amount: int,
        source: str,
        description: str = "",
    ) -> bool:
        """Award points to user"""

        # Get user points
        result = await session.execute(
            select(UserPoints).where(
                UserPoints.user_id == user_id,
                UserPoints.group_id == group_id,
                UserPoints.deleted_at.is_(None),
            )
        )
        user_points = result.scalar_one_or_none()

        if not user_points:
            user_points = await self.initialize_user_points(user_id, group_id)

        # Update balance
        old_balance = user_points.current_points
        user_points.current_points += amount
        user_points.total_earned += amount
        user_points.last_activity = int(time.time())

        # Update level and experience
        await self._update_level_and_experience(user_points, amount)

        # Record transaction
        transaction = PointTransaction(
            user_id=user_id,
            group_id=group_id,
            transaction_type="earn",
            amount=amount,
            balance_before=old_balance,
            balance_after=user_points.current_points,
            source=source,
            description=description,
            transaction_time=int(time.time()),
        )
        session.add(transaction)

        await session.flush()
        return True

    async def spend_points(
        self,
        session: AsyncSession,
        user_id: int,
        group_id: int,
        amount: int,
        source: str,
        description: str = "",
    ) -> tuple[bool, str]:
        """Spend points from user"""

        # Get user points
        result = await session.execute(
            select(UserPoints).where(
                UserPoints.user_id == user_id,
                UserPoints.group_id == group_id,
                UserPoints.deleted_at.is_(None),
            )
        )
        user_points = result.scalar_one_or_none()

        if not user_points:
            return False, "User points not found"

        if user_points.current_points < amount:
            return False, "Insufficient points"

        # Update balance
        old_balance = user_points.current_points
        user_points.current_points -= amount
        user_points.total_spent += amount
        user_points.last_activity = int(time.time())

        # Record transaction
        transaction = PointTransaction(
            user_id=user_id,
            group_id=group_id,
            transaction_type="spend",
            amount=-amount,
            balance_before=old_balance,
            balance_after=user_points.current_points,
            source=source,
            description=description,
            transaction_time=int(time.time()),
        )
        session.add(transaction)

        await session.flush()
        return True, "Points spent successfully"

    async def _update_level_and_experience(
        self, user_points: UserPoints, points_earned: int
    ):
        """Update user level and experience"""

        user_points.experience += points_earned

        # Check for level up
        current_level = user_points.level
        next_level = current_level + 1

        if next_level in self.LEVEL_REQUIREMENTS:
            required_points = self.LEVEL_REQUIREMENTS[next_level]["points"]
            if user_points.total_earned >= required_points:
                user_points.level = next_level

    async def get_user_points(self, user_id: int, group_id: int) -> dict | None:
        """Get user point information"""

        async with async_session_factory() as session:
            result = await session.execute(
                select(UserPoints).where(
                    UserPoints.user_id == user_id,
                    UserPoints.group_id == group_id,
                    UserPoints.deleted_at.is_(None),
                )
            )
            user_points = result.scalar_one_or_none()

            if not user_points:
                return None

            level_info = self.LEVEL_REQUIREMENTS.get(user_points.level, {})
            next_level_info = self.LEVEL_REQUIREMENTS.get(user_points.level + 1, {})

            return {
                "current_points": user_points.current_points,
                "total_earned": user_points.total_earned,
                "total_spent": user_points.total_spent,
                "level": user_points.level,
                "level_name": level_info.get("name", "Unknown"),
                "experience": user_points.experience,
                "streak_days": user_points.streak_days,
                "bonus_multiplier": level_info.get("bonus", 1.0),
                "next_level_points": next_level_info.get("points", 0),
                "selected_apploid": user_points.selected_apploid,
            }

    async def get_user_apploids(self, user_id: int, group_id: int) -> list[dict]:
        """Get user's owned apploids"""

        async with async_session_factory() as session:
            result = await session.execute(
                select(UserApploid, Apploid)
                .join(Apploid)
                .where(UserApploid.user_id == user_id, UserApploid.group_id == group_id)
            )
            apploids = result.all()

            return [
                {
                    "apploid_id": user_apploid.apploid_id,
                    "name": apploid.apploid_name,
                    "emoji": apploid.apploid_emoji,
                    "rarity": apploid.rarity,
                    "is_equipped": user_apploid.is_equipped,
                    "purchase_price": user_apploid.purchase_price,
                    "acquired_at": user_apploid.acquired_at,
                }
                for user_apploid, apploid in apploids
            ]

    async def get_available_apploids(self, user_id: int, group_id: int) -> list[dict]:
        """Get apploids available for user to purchase"""

        user_points_info = await self.get_user_points(user_id, group_id)
        if not user_points_info:
            return []

        user_level = user_points_info["level"]
        current_points = user_points_info["current_points"]
        owned_apploids = await self.get_user_apploids(user_id, group_id)
        {app["apploid_id"] for app in owned_apploids}

        # Get all apploids user can access
        available = []
        for apploid_data in self.DEFAULT_APPLOIDS:
            if (
                apploid_data["required_level"] <= user_level
                and apploid_data["required_points"] <= current_points
                and apploid_data["name"] not in [app["name"] for app in owned_apploids]
            ):
                available.append(
                    {
                        "name": apploid_data["name"],
                        "emoji": apploid_data["emoji"],
                        "description": apploid_data["description"],
                        "rarity": apploid_data["rarity"],
                        "required_level": apploid_data["required_level"],
                        "required_points": apploid_data["required_points"],
                    }
                )

        return sorted(available, key=lambda x: (x["required_points"], x["name"]))

    async def purchase_apploid(
        self, user_id: int, group_id: int, apploid_name: str
    ) -> tuple[bool, str]:
        """Purchase an apploid"""

        async with async_session_factory() as session:
            async with session.begin():
                # Get user points
                user_points_info = await self.get_user_points(user_id, group_id)
                if not user_points_info:
                    return False, "User not found"

                # Find apploid
                apploid_data = None
                for apploid in self.DEFAULT_APPLOIDS:
                    if apploid["name"] == apploid_name:
                        apploid_data = apploid
                        break

                if not apploid_data:
                    return False, "Apploid not found"

                # Check requirements
                if (
                    apploid_data["required_level"] > user_points_info["level"]
                    or apploid_data["required_points"]
                    > user_points_info["current_points"]
                ):
                    return False, "Requirements not met"

                # Check if already owned
                owned_apploids = await self.get_user_apploids(user_id, group_id)
                if apploid_name in [app["name"] for app in owned_apploids]:
                    return False, "Already owned"

                # Spend points
                success, message = await self.spend_points(
                    session,
                    user_id,
                    group_id,
                    apploid_data["required_points"],
                    "apploid_purchase",
                    f"Purchased {apploid_name}",
                )

                if not success:
                    return False, message

                # Fetch actual apploid_id
                apploid_result = await session.execute(
                    select(Apploid).where(Apploid.apploid_name == apploid_name)
                )
                apploid_record = apploid_result.scalar_one_or_none()
                if not apploid_record:
                    return False, "Apploid database record not found"

                # Create apploid record
                user_apploid = UserApploid(
                    user_id=user_id,
                    group_id=group_id,
                    apploid_id=apploid_record.apploid_id,
                    is_equipped=False,
                    purchase_price=apploid_data["required_points"],
                    acquired_at=int(time.time()),
                )
                session.add(user_apploid)

                await session.flush()
                return True, f"Successfully purchased {apploid_name}!"

    async def equip_apploid(
        self, user_id: int, group_id: int, apploid_name: str
    ) -> tuple[bool, str]:
        """Equip an apploid"""

        async with async_session_factory() as session:
            async with session.begin():
                # Get user points
                result = await session.execute(
                    select(UserPoints).where(
                        UserPoints.user_id == user_id,
                        UserPoints.group_id == group_id,
                        UserPoints.deleted_at.is_(None),
                    )
                )
                user_points = result.scalar_one_or_none()

                if not user_points:
                    return False, "User not found"

                # Check if owned
                owned_apploids = await self.get_user_apploids(user_id, group_id)
                if apploid_name not in [app["name"] for app in owned_apploids]:
                    return False, "Apploid not owned"

                # Update selected apploid
                user_points.selected_apploid = apploid_name
                await session.flush()

                return True, f"Equipped {apploid_name}!"

    async def get_leaderboard(self, group_id: int, limit: int = 10) -> list[dict]:
        """Get point leaderboard for group"""

        async with async_session_factory() as session:
            result = await session.execute(
                select(UserPoints)
                .where(
                    UserPoints.group_id == group_id,
                    UserPoints.deleted_at.is_(None),
                )
                .order_by(UserPoints.current_points.desc())
                .limit(limit)
            )
            users = result.scalars().all()

            leaderboard = []
            rank = 1
            for user_points in users:
                level_info = self.LEVEL_REQUIREMENTS.get(user_points.level, {})

                leaderboard.append(
                    {
                        "rank": rank,
                        "user_id": user_points.user_id,
                        "points": user_points.current_points,
                        "level": user_points.level,
                        "level_name": level_info.get("name", "Unknown"),
                        "selected_apploid": user_points.selected_apploid,
                    }
                )
                rank += 1

            return leaderboard

    async def process_activity(
        self, user_id: int, group_id: int, activity_type: str, description: str = ""
    ) -> tuple[bool, int, str]:
        """Process point-earning activity"""

        # Check cooldown
        cooldown_key = f"{user_id}_{group_id}_{activity_type}"
        if activity_type in self.EARNING_ACTIVITIES:
            cooldown = self.EARNING_ACTIVITIES[activity_type]["cooldown"]
            if cooldown_key in self.cooldowns:
                if time.time() - self.cooldowns[cooldown_key] < cooldown:
                    return False, 0, "Activity on cooldown"

        # Get activity details
        activity = self.EARNING_ACTIVITIES.get(activity_type)
        if not activity:
            return False, 0, "Unknown activity"

        # Calculate points with bonus
        user_points_info = await self.get_user_points(user_id, group_id)
        if not user_points_info:
            user_points_info = await self.initialize_user_points(user_id, group_id)

        bonus = user_points_info.get("bonus_multiplier", 1.0)
        points_earned = int(activity["points"] * bonus)

        # Award points
        async with async_session_factory() as session:
            success = await self.award_points(
                session,
                user_id,
                group_id,
                points_earned,
                activity_type,
                description or activity["description"],
            )

            if success:
                # Update cooldown
                self.cooldowns[cooldown_key] = time.time()
                return True, points_earned, f"Earned {points_earned} points!"

        return False, 0, "Failed to award points"

    async def get_point_stats(self, group_id: int) -> dict:
        """Get point statistics for group"""

        async with async_session_factory() as session:
            # Get total users with points
            result = await session.execute(
                select(UserPoints).where(
                    UserPoints.group_id == group_id,
                    UserPoints.deleted_at.is_(None),
                )
            )
            users = result.scalars().all()

            if not users:
                return {
                    "total_users": 0,
                    "total_points": 0,
                    "total_earned": 0,
                    "total_spent": 0,
                    "average_points": 0,
                    "highest_level": 1,
                    "apploids_owned": 0,
                }

            total_points = sum(user.current_points for user in users)
            total_earned = sum(user.total_earned for user in users)
            total_spent = sum(user.total_spent for user in users)
            highest_level = max(user.level for user in users)

            return {
                "total_users": len(users),
                "total_points": total_points,
                "total_earned": total_earned,
                "total_spent": total_spent,
                "average_points": total_points // len(users),
                "highest_level": highest_level,
                "apploids_owned": 0,  # Would calculate from user_apploids
            }


# Global point service instance
point_service = PointService()

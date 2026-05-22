from __future__ import annotations

import time

from sqlalchemy import select
from telegram import Chat, Update
from telegram.ext import ContextTypes

from src.bot.database import async_session_factory
from src.bot.models.features import (
    FeatureLog,
    FeatureUsage,
    GroupFeature,
)
from src.bot.services.acn_service import ACNService


class FeatureService:
    """Comprehensive bot feature management service"""

    # Define all available bot features
    AVAILABLE_FEATURES = {
        # Core moderation features
        "moderation": {
            "name": "Moderation Commands",
            "description": "Ban, kick, warn, mute commands",
            "category": "moderation",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "filters": {
            "name": "Message Filters",
            "description": "Word filters and auto-moderation",
            "category": "moderation",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "swear_words": {
            "name": "Swear Word Detection",
            "description": "Automatic swear word detection and punishment",
            "category": "moderation",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "flood_control": {
            "name": "Flood Control",
            "description": "Anti-spam and flood protection",
            "category": "moderation",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        # AI and smart features
        "ai_moderation": {
            "name": "AI Moderation",
            "description": "AI-powered content analysis and moderation",
            "category": "ai",
            "default_enabled": False,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "smart_filters": {
            "name": "Smart Filters",
            "description": "AI-enhanced message filtering",
            "category": "ai",
            "default_enabled": False,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        # User engagement features
        "welcome": {
            "name": "Welcome Messages",
            "description": "Automatic welcome for new users",
            "category": "engagement",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "goodbye": {
            "name": "Goodbye Messages",
            "description": "Automatic goodbye for leaving users",
            "category": "engagement",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "user_info": {
            "name": "User Information",
            "description": "User stats and information commands",
            "category": "engagement",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["member", "admin", "captain", "commander"],
        },
        # Fun and entertainment features
        "nico_moments": {
            "name": "Nico Robin Moments",
            "description": "Robin's character interactions and emotions",
            "category": "entertainment",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["member", "admin", "captain", "commander"],
        },
        "flirting": {
            "name": "Flirting System",
            "description": "Romantic interactions with Nico Robin",
            "category": "entertainment",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["member", "admin", "captain", "commander"],
        },
        "fun": {
            "name": "Fun Commands",
            "description": "Entertainment and fun commands",
            "category": "entertainment",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["member", "admin", "captain", "commander"],
        },
        # Utility features
        "notes": {
            "name": "Note System",
            "description": "Save and retrieve notes",
            "category": "utility",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "stats": {
            "name": "Statistics",
            "description": "Group and user statistics",
            "category": "utility",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "scheduler": {
            "name": "Task Scheduler",
            "description": "Scheduled tasks and reminders",
            "category": "utility",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        # Federation features
        "federation": {
            "name": "Federation System",
            "description": "Cross-group federation management",
            "category": "federation",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        # ACN features
        "acn_loyalty": {
            "name": "ACN Loyalty System",
            "description": "Anime Crew Network loyalty points and ranks",
            "category": "acn",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["member", "admin", "captain", "commander"],
        },
        "acn_broadcast": {
            "name": "ACN Broadcast System",
            "description": "Channel broadcasting to ACN groups",
            "category": "acn",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["captain", "commander"],
        },
        # Advanced features
        "realtime_events": {
            "name": "Real-time Events",
            "description": "WebSocket real-time event broadcasting",
            "category": "advanced",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "captcha": {
            "name": "CAPTCHA System",
            "description": "CAPTCHA verification for new users",
            "category": "security",
            "default_enabled": False,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "purge": {
            "name": "Message Purge",
            "description": "Bulk message deletion",
            "category": "moderation",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
        "settings": {
            "name": "Group Settings",
            "description": "Group configuration and preferences",
            "category": "utility",
            "default_enabled": True,
            "owner_only": False,
            "permissions": ["admin", "captain", "commander"],
        },
    }

    @staticmethod
    async def is_feature_enabled(
        group_id: int, feature_name: str, user_id: int | None = None
    ) -> bool:
        """Check if a feature is enabled for a group"""

        # Check if feature exists
        if feature_name not in FeatureService.AVAILABLE_FEATURES:
            return False

        async with async_session_factory() as session:
            # Get feature flag for this group
            result = await session.execute(
                select(GroupFeature).where(
                    GroupFeature.group_id == group_id,
                    GroupFeature.feature_name == feature_name,
                )
            )
            toggle = result.scalar_one_or_none()

            # If no toggle exists, use default
            if toggle is None:
                return FeatureService.AVAILABLE_FEATURES[feature_name][
                    "default_enabled"
                ]

            return toggle.enabled

    @staticmethod
    async def can_use_feature(
        group_id: int, feature_name: str, user_id: int
    ) -> tuple[bool, str]:
        """Check if user can use a feature"""

        # Check if feature exists
        if feature_name not in FeatureService.AVAILABLE_FEATURES:
            return False, "Feature not found"

        feature_info = FeatureService.AVAILABLE_FEATURES[feature_name]

        # Check if feature is enabled
        if not await FeatureService.is_feature_enabled(group_id, feature_name):
            return False, "Feature is disabled"

        # Get user role
        user_role = await ACNService.get_user_role(user_id)

        # Check permissions
        if user_role not in feature_info["permissions"]:
            return (
                False,
                f"Permission denied. Required: {', '.join(feature_info['permissions'])}",
            )

        return True, "Permission granted"

    @staticmethod
    async def toggle_feature(
        group_id: int,
        feature_name: str,
        enabled: bool,
        user_id: int,
        reason: str | None = None,
        toggle_level: str = "group",
        chat: Chat | None = None,
        context: ContextTypes.DEFAULT_TYPE | None = None,
    ) -> tuple[bool, str]:
        """Toggle a feature on/off"""

        # Check if feature exists
        if feature_name not in FeatureService.AVAILABLE_FEATURES:
            return False, "Feature not found"

        feature_info = FeatureService.AVAILABLE_FEATURES[feature_name]

        # Check if user can toggle this feature
        user_role = await ACNService.get_user_role(user_id)

        # Only captains and commanders can toggle features
        if user_role not in ["captain", "commander"]:
            return False, "Only captains and commanders can toggle features"

        async with async_session_factory() as session:
            async with session.begin():
                # Get existing toggle
                result = await session.execute(
                    select(GroupFeature).where(
                        GroupFeature.group_id == group_id,
                        GroupFeature.feature_name == feature_name,
                    )
                )
                toggle = result.scalar_one_or_none()

                old_value = (
                    toggle.enabled if toggle else feature_info["default_enabled"]
                )

                # Create or update toggle
                if toggle is None:
                    toggle = GroupFeature(
                        group_id=group_id,
                        feature_name=feature_name,
                        enabled=enabled,
                    )
                    session.add(toggle)
                else:
                    toggle.enabled = enabled

                # Log the change
                log = FeatureLog(
                    group_id=group_id,
                    user_id=user_id,
                    feature_name=feature_name,
                    action="enabled" if enabled else "disabled",
                    old_value=old_value,
                    new_value=enabled,
                    reason=reason,
                    toggle_level=toggle_level,
                )
                session.add(log)

                await session.flush()

                return (
                    True,
                    f"Feature {feature_name} {'enabled' if enabled else 'disabled'} successfully",
                )

    @staticmethod
    async def get_feature_status(group_id: int) -> dict[str, dict]:
        """Get status of all features for a group"""

        async with async_session_factory() as session:
            # Get all toggles for this group
            result = await session.execute(
                select(GroupFeature).where(GroupFeature.group_id == group_id)
            )
            toggles = {toggle.feature_name: toggle for toggle in result.scalars().all()}

            # Build status dictionary
            status = {}
            for feature_name, feature_info in FeatureService.AVAILABLE_FEATURES.items():
                toggle = toggles.get(feature_name)
                status[feature_name] = {
                    "name": feature_info["name"],
                    "description": feature_info["description"],
                    "category": feature_info["category"],
                    "is_enabled": (
                        toggle.enabled if toggle else feature_info["default_enabled"]
                    ),
                    "default_enabled": feature_info["default_enabled"],
                    "toggled_by": None,
                    "toggle_reason": None,
                    "updated_at": None,
                    "permissions": feature_info["permissions"],
                    "owner_only": feature_info["owner_only"],
                }

            return status

    @staticmethod
    async def get_features_by_category(category: str) -> dict[str, dict]:
        """Get all features in a specific category"""

        return {
            name: info
            for name, info in FeatureService.AVAILABLE_FEATURES.items()
            if info["category"] == category
        }

    @staticmethod
    async def log_feature_usage(group_id: int, user_id: int, feature_name: str) -> None:
        """Log feature usage for statistics"""

        async with async_session_factory() as session:
            async with session.begin():
                # Get existing usage record
                result = await session.execute(
                    select(FeatureUsage).where(
                        FeatureUsage.group_id == group_id,
                        FeatureUsage.user_id == user_id,
                        FeatureUsage.feature_name == feature_name,
                    )
                )
                usage = result.scalar_one_or_none()

                if usage is None:
                    usage = FeatureUsage(
                        group_id=group_id,
                        user_id=user_id,
                        feature_name=feature_name,
                        usage_count=1,
                        last_used=int(time.time()),
                    )
                    session.add(usage)
                else:
                    usage.usage_count += 1
                    usage.last_used = int(time.time())

                await session.flush()

    @staticmethod
    async def get_feature_usage_stats(
        group_id: int, feature_name: str | None = None
    ) -> list[dict]:
        """Get feature usage statistics"""

        async with async_session_factory() as session:
            query = select(FeatureUsage).where(FeatureUsage.group_id == group_id)

            if feature_name:
                query = query.where(FeatureUsage.feature_name == feature_name)

            result = await session.execute(
                query.order_by(FeatureUsage.usage_count.desc())
            )
            usages = result.scalars().all()

            stats = []
            for usage in usages:
                stats.append(
                    {
                        "feature_name": usage.feature_name,
                        "user_id": usage.user_id,
                        "usage_count": usage.usage_count,
                        "last_used": usage.last_used,
                    }
                )

            return stats

    @staticmethod
    async def get_feature_logs(
        group_id: int, feature_name: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Get feature toggle logs"""

        async with async_session_factory() as session:
            query = select(FeatureLog).where(FeatureLog.group_id == group_id)

            if feature_name:
                query = query.where(FeatureLog.feature_name == feature_name)

            result = await session.execute(
                query.order_by(FeatureLog.created_at.desc()).limit(limit)
            )
            logs = result.scalars().all()

            log_list = []
            for log in logs:
                log_list.append(
                    {
                        "feature_name": log.feature_name,
                        "action": log.action,
                        "old_value": log.old_value,
                        "new_value": log.new_value,
                        "reason": log.reason,
                        "user_id": log.user_id,
                        "toggle_level": log.toggle_level,
                        "created_at": (
                            log.created_at.isoformat() if log.created_at else None
                        ),
                    }
                )

            return log_list

    @staticmethod
    def get_all_features() -> dict[str, dict]:
        """Get all available features"""
        return FeatureService.AVAILABLE_FEATURES.copy()

    @staticmethod
    def get_categories() -> list[str]:
        """Get all feature categories"""
        categories = set()
        for feature in FeatureService.AVAILABLE_FEATURES.values():
            categories.add(feature["category"])
        return sorted(list(categories))


# Decorator for feature checking
def feature_required(feature_name: str):
    """Decorator to check if feature is enabled before executing command"""

    def decorator(func):
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            if not update.effective_chat or not update.effective_user:
                return

            # Check if feature is enabled
            can_use, message = await FeatureService.can_use_feature(
                update.effective_chat.id, feature_name, update.effective_user.id
            )

            if not can_use:
                if update.message:
                    await update.message.reply_text(f"🚫 {message}")
                return

            # Log feature usage
            await FeatureService.log_feature_usage(
                update.effective_chat.id, update.effective_user.id, feature_name
            )

            # Execute the original function
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator


# Global feature service instance
feature_service = FeatureService()

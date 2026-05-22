from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import User as TelegramUser

from src.bot.models.user import User


class UserService:
    @staticmethod
    async def get_user(session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(
            select(User).where(User.user_id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_username(session: AsyncSession, username: str) -> User | None:
        normalized = username.removeprefix("@").lower()
        result = await session.execute(
            select(User)
            .where(User.username == normalized, User.deleted_at.is_(None))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def ensure_user(session: AsyncSession, telegram_user: TelegramUser) -> User:
        result = await session.execute(
            select(User).where(User.user_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()
        username = telegram_user.username.lower() if telegram_user.username else None
        if user is None:
            user = User(
                user_id=telegram_user.id,
                username=username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                is_bot=telegram_user.is_bot,
                join_date=datetime.now(UTC),
            )
            session.add(user)
        else:
            user.username = username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.is_bot = telegram_user.is_bot
            user.deleted_at = None
        await session.flush()
        return user

    @staticmethod
    async def ensure_minimal_user(
        session: AsyncSession,
        user_id: int,
        username: str | None = None,
    ) -> User:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(user_id=user_id, username=username, join_date=datetime.now(UTC))
            session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def increment_ban_count(session: AsyncSession, user_id: int) -> None:
        await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(ban_count=User.ban_count + 1)
        )

    @staticmethod
    async def increment_warn_count(session: AsyncSession, user_id: int) -> None:
        await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(warn_count=User.warn_count + 1)
        )

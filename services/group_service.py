from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Chat

from config import settings
from models.group import Group


class GroupService:
    @staticmethod
    async def get_group(session: AsyncSession, group_id: int) -> Group | None:
        result = await session.execute(select(Group).where(Group.group_id == group_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def ensure_group(session: AsyncSession, chat: Chat) -> Group:
        result = await session.execute(select(Group).where(Group.group_id == chat.id))
        group = result.scalar_one_or_none()
        if group is None:
            group = Group(
                group_id=chat.id,
                title=chat.title or chat.full_name or str(chat.id),
                locale=settings.default_locale,
                prefix=settings.default_prefix,
            )
            session.add(group)
        else:
            group.title = chat.title or chat.full_name or group.title
        await session.flush()
        return group

    @staticmethod
    async def update_settings(
        session: AsyncSession,
        group_id: int,
        **values: Any,
    ) -> Group:
        result = await session.execute(select(Group).where(Group.group_id == group_id))
        group = result.scalar_one()
        for key, value in values.items():
            if hasattr(group, key):
                setattr(group, key, value)
            else:
                raise ValueError(f"Unknown setting: {key}")
        await session.flush()
        return group

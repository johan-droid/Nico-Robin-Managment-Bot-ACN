from __future__ import annotations

import asyncio
import time
from typing import Any


class AdminCache:
    """Caches Telegram admins per group with TTL and background refresh support."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._data: dict[int, set[int]] = {}
        self._updated_at: dict[int, float] = {}
        self._lock = asyncio.Lock()

    async def get_admins(self, bot: Any, group_id: int) -> set[int]:
        async with self._lock:
            now = time.monotonic()
            stale = (now - self._updated_at.get(group_id, 0.0)) > self._ttl
            if stale or group_id not in self._data:
                admins = await bot.get_chat_administrators(group_id)
                self._data[group_id] = {admin.user.id for admin in admins}
                self._updated_at[group_id] = now
            return set(self._data[group_id])

    async def is_admin(self, bot: Any, group_id: int, user_id: int) -> bool:
        admins = await self.get_admins(bot, group_id)
        return user_id in admins

    async def remember_group(self, group_id: int) -> None:
        async with self._lock:
            self._updated_at.setdefault(group_id, 0.0)

    async def refresh_known_groups(self, bot: Any) -> None:
        async with self._lock:
            groups = list(self._updated_at.keys())
        for group_id in groups:
            try:
                await self.get_admins(bot, group_id)
            except Exception:
                continue

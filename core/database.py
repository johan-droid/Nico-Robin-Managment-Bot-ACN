from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite


class Database:
    _instance: "Database | None" = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db_path = Path(os.getenv("NICO_ROBIN_DB_PATH", "nico_robin_bot.sqlite3"))
            cls._instance._connection = None
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    @property
    def path(self) -> Path:
        return self._db_path

    async def connect(self) -> None:
        if self._connection is not None:
            return

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(str(self._db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.execute("PRAGMA synchronous = NORMAL")
        await self._connection.execute("PRAGMA busy_timeout = 5000")
        await self._connection.commit()

    async def close(self) -> None:
        if self._connection is None:
            return
        await self._connection.close()
        self._connection = None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        async with self._lock:
            cursor = await self._connection.execute(sql, params)
            await self._connection.commit()
            return cursor.lastrowid

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> Any | None:
        async with self._lock:
            cursor = await self._connection.execute(sql, params)
            return await cursor.fetchone()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
        async with self._lock:
            cursor = await self._connection.execute(sql, params)
            return await cursor.fetchall()

    async def executemany(self, sql: str, values: list[tuple[Any, ...]]) -> None:
        async with self._lock:
            await self._connection.executemany(sql, values)
            await self._connection.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._lock:
            try:
                yield self._connection
                await self._connection.commit()
            except Exception:
                await self._connection.rollback()
                raise

    async def executescript(self, script: str) -> None:
        async with self._lock:
            await self._connection.executescript(script)
            await self._connection.commit()


database = Database()

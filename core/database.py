from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS group_features (
    group_id INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (group_id, feature_name)
);

CREATE TABLE IF NOT EXISTS acn_whitelist (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    role TEXT NOT NULL CHECK(role IN ('Captain', 'Commander', 'Member')),
    added_by INTEGER NOT NULL,
    added_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_points (
    user_id INTEGER PRIMARY KEY,
    points INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    last_message_time INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS point_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS moderation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    moderator_id INTEGER NOT NULL,
    target_id INTEGER,
    group_id INTEGER NOT NULL,
    reason TEXT,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS broadcast_sources (
    channel_id INTEGER PRIMARY KEY,
    channel_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS broadcast_targets (
    group_id INTEGER PRIMARY KEY,
    group_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS feature_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    changed_by INTEGER NOT NULL,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS warns (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    warn_count INTEGER NOT NULL DEFAULT 0,
    last_reason TEXT,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS welcome_settings (
    group_id INTEGER PRIMARY KEY,
    welcome_enabled INTEGER NOT NULL DEFAULT 1,
    welcome_text TEXT,
    farewell_enabled INTEGER NOT NULL DEFAULT 1,
    farewell_text TEXT,
    clean_welcome INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notes (
    group_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    saved_by INTEGER NOT NULL,
    saved_at INTEGER NOT NULL,
    PRIMARY KEY (group_id, name)
);

CREATE TABLE IF NOT EXISTS chat_filters (
    group_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    reply_text TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT 'reply',
    PRIMARY KEY (group_id, keyword)
);

CREATE TABLE IF NOT EXISTS flirt_stats (
    user_id INTEGER PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS friendship (
    user_id INTEGER PRIMARY KEY,
    bond_points INTEGER NOT NULL DEFAULT 0,
    last_interaction INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    reporter_id INTEGER NOT NULL,
    target_id INTEGER,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    handled_by INTEGER,
    created_at INTEGER NOT NULL,
    handled_at INTEGER
);

CREATE TABLE IF NOT EXISTS federation_groups (
    fed_id TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    PRIMARY KEY (fed_id, group_id)
);

CREATE TABLE IF NOT EXISTS federation_bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fed_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    banned_by INTEGER NOT NULL,
    reason TEXT,
    created_at INTEGER NOT NULL
);
"""


class DatabaseManager:
    """Async SQLite singleton with serialized writes."""

    _instance: DatabaseManager | None = None
    _instance_lock = asyncio.Lock()

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, db_path: str | None = None) -> DatabaseManager:
        async with cls._instance_lock:
            if cls._instance is None:
                resolved = db_path or os.getenv("BOT_DB_PATH", "data/nico_robin.db")
                cls._instance = cls(resolved)
        return cls._instance

    async def initialize(self) -> None:
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        async with self._lock:
            await self._conn.executescript(SCHEMA_SQL)
            await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        conn = self._require_conn()
        async with self._lock:
            await conn.execute(query, params)
            await conn.commit()

    async def fetchone(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> dict[str, Any] | None:
        conn = self._require_conn()
        async with self._lock:
            cursor = await conn.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> list[dict[str, Any]]:
        conn = self._require_conn()
        async with self._lock:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def execute_returning_id(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> int:
        conn = self._require_conn()
        async with self._lock:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return int(cursor.lastrowid)

    async def is_role(self, user_id: int, role: str) -> bool:
        row = await self.fetchone(
            """
            SELECT 1
            FROM acn_whitelist
            WHERE user_id = ? AND role = ?
            """,
            (user_id, role),
        )
        return row is not None

    async def is_captain(self, user_id: int) -> bool:
        return await self.is_role(user_id, "Captain")

    async def is_commander(self, user_id: int) -> bool:
        return await self.is_role(user_id, "Commander")

    async def is_member(self, user_id: int) -> bool:
        row = await self.fetchone(
            """
            SELECT role
            FROM acn_whitelist
            WHERE user_id = ?
            """,
            (user_id,),
        )
        return row is not None

    async def get_user_role(self, user_id: int) -> str | None:
        row = await self.fetchone(
            "SELECT role FROM acn_whitelist WHERE user_id = ?",
            (user_id,),
        )
        return str(row["role"]) if row else None

    async def get_feature_enabled(self, group_id: int, feature_name: str) -> bool:
        row = await self.fetchone(
            """
            SELECT enabled
            FROM group_features
            WHERE group_id = ? AND feature_name = ?
            """,
            (group_id, feature_name),
        )
        if row is None:
            return True
        return bool(row["enabled"])

    async def set_feature_enabled(
        self,
        group_id: int,
        feature_name: str,
        enabled: bool,
        changed_by: int,
    ) -> None:
        now = int(time.time())
        await self.execute(
            """
            INSERT INTO group_features (group_id, feature_name, enabled, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(group_id, feature_name)
            DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at
            """,
            (group_id, feature_name, int(enabled), now),
        )
        await self.execute(
            """
            INSERT INTO feature_logs (feature_name, group_id, action, changed_by, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                feature_name,
                group_id,
                "enable" if enabled else "disable",
                changed_by,
                now,
            ),
        )

    async def log_moderation(
        self,
        action_type: str,
        moderator_id: int,
        target_id: int | None,
        group_id: int,
        reason: str | None,
    ) -> None:
        await self.execute(
            """
            INSERT INTO moderation_log (action_type, moderator_id, target_id, group_id, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (action_type, moderator_id, target_id, group_id, reason, int(time.time())),
        )

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("DatabaseManager is not initialized")
        return self._conn

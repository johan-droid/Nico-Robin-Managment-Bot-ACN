from __future__ import annotations

import asyncio
from pathlib import Path

from core.database import database

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS captains (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS commanders (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS group_features (
    group_id INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, feature_name)
);

CREATE TABLE IF NOT EXISTS acn_whitelist (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    role TEXT NOT NULL CHECK(role IN ('Captain', 'Commander', 'Member')),
    added_by INTEGER,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_points (
    user_id INTEGER NOT NULL,
    points INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    last_message_time INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS point_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    transaction_uid TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS moderation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    moderator_id INTEGER,
    target_id INTEGER,
    group_id INTEGER,
    reason TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS broadcast_sources (
    channel_id INTEGER PRIMARY KEY,
    channel_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS broadcast_targets (
    group_id INTEGER PRIMARY KEY,
    group_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS feature_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    changed_by INTEGER,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_name TEXT NOT NULL,
    user_id INTEGER,
    chat_id INTEGER,
    payload TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    error_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_starts (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    start_param TEXT,
    start_count INTEGER NOT NULL DEFAULT 1,
    first_started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_started_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS group_settings (
    group_id INTEGER PRIMARY KEY,
    welcome_text TEXT,
    farewell_text TEXT,
    rules_text TEXT,
    welcome_enabled INTEGER NOT NULL DEFAULT 1,
    farewell_enabled INTEGER NOT NULL DEFAULT 1,
    clean_welcome INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warnings (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    warnings INTEGER NOT NULL DEFAULT 0,
    last_warned_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    reporter_id INTEGER NOT NULL,
    target_id INTEGER,
    target_message_id INTEGER,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    handled_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    handled_at TEXT
);

CREATE TABLE IF NOT EXISTS flirt_stats (
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    current_streak INTEGER NOT NULL DEFAULT 0,
    best_streak INTEGER NOT NULL DEFAULT 0,
    last_attempt_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS flirt_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    trigger_word TEXT,
    success INTEGER NOT NULL DEFAULT 0,
    response TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS friendship_state (
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    bond_points INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    last_interaction_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS friendship_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    group_id INTEGER NOT NULL,
    note_name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_by INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, note_name)
);

CREATE TABLE IF NOT EXISTS filters (
    group_id INTEGER NOT NULL,
    pattern TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT 'delete',
    response TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, pattern)
);

CREATE TABLE IF NOT EXISTS broadcast_state (
    channel_id INTEGER PRIMARY KEY,
    last_message_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS broadcast_deliveries (
    source_channel_id INTEGER NOT NULL,
    source_message_id INTEGER NOT NULL,
    destination_group_id INTEGER NOT NULL,
    destination_message_id INTEGER NOT NULL,
    destination_message_kind TEXT NOT NULL DEFAULT 'copy',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_channel_id, source_message_id, destination_group_id)
);
"""


async def initialize_database() -> None:
    await database.connect()
    await database.executescript(SCHEMA_SQL)


if __name__ == "__main__":
    asyncio.run(initialize_database())

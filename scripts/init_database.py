#!/usr/bin/env python3
"""
Database initialization helper.

This script is designed for local/dev bootstrap where tables may already exist.
It creates missing tables, applies a small compatibility patch for legacy schemas,
records Alembic revision state, and seeds baseline data.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from alembic.config import Config as AlembicConfig  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.bot.database import engine  # noqa: E402
from src.bot.models import Base  # noqa: E402

# Idempotent schema compatibility patches for existing databases that were
# bootstrapped before recent model changes landed.
SCHEMA_PATCHES: tuple[tuple[str, str, str], ...] = (
    ("groups", "locked_media", "JSON NOT NULL DEFAULT '{}'::json"),
    ("groups", "nightmode_enabled", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("groups", "welcome_dm_text", "TEXT"),
    ("groups", "welcome_dm_enabled", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "deleted_at", "TIMESTAMPTZ"),
    ("warns", "deleted_at", "TIMESTAMPTZ"),
    ("notes", "deleted_at", "TIMESTAMPTZ"),
    ("member_profiles", "deleted_at", "TIMESTAMPTZ"),
    ("loyalty_points", "deleted_at", "TIMESTAMPTZ"),
    ("user_points", "deleted_at", "TIMESTAMPTZ"),
    ("flirting_stats", "deleted_at", "TIMESTAMPTZ"),
    ("user_points", "last_earned", "BIGINT NOT NULL DEFAULT 0"),
    ("point_transactions", "transaction_uid", "VARCHAR(64)"),
)


def log(message: str) -> None:
    """Best-effort logging that won't crash on limited terminal encodings."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="backslashreplace").decode("ascii"))


def _get_alembic_heads() -> tuple[str, ...]:
    cfg = AlembicConfig(str(project_root / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    return tuple(script.get_heads())


async def _ensure_alembic_version_capacity() -> None:
    """Ensure Alembic can store this project's long revision IDs."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(128) NOT NULL PRIMARY KEY)"
            )
        )
        result = await conn.execute(
            text(
                "SELECT character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_schema='public' "
                "AND table_name='alembic_version' "
                "AND column_name='version_num'"
            )
        )
        current_length = result.scalar_one_or_none()
        if current_length is None or current_length < 128:
            await conn.execute(
                text(
                    "ALTER TABLE alembic_version "
                    "ALTER COLUMN version_num TYPE VARCHAR(128)"
                )
            )


async def _record_alembic_heads() -> None:
    """Write current repository heads into alembic_version without running env.py."""
    heads = await asyncio.to_thread(_get_alembic_heads)
    if not heads:
        raise RuntimeError("No Alembic heads found in script directory.")

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM alembic_version"))
        for revision in heads:
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )


async def _apply_schema_patches() -> None:
    """Apply idempotent ALTER statements for known legacy-schema gaps."""
    log("🛠️  Applying schema compatibility patches...")
    async with engine.begin() as conn:
        for table_name, column_name, definition in SCHEMA_PATCHES:
            await conn.execute(
                text(
                    f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{column_name}" {definition}'
                )
            )
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ix_point_transactions_transaction_uid "
                "ON point_transactions (transaction_uid)"
            )
        )
    log("✅ Schema compatibility patches applied!")


async def init_database() -> bool:
    """Initialize the database with all tables and baseline seed data."""

    log("🚀 Database Initialization")
    log("=" * 40)

    try:
        # Create all tables
        log("📋 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        log("✅ Database tables created successfully!")

        # Backfill legacy columns that create_all won't add on existing tables.
        await _apply_schema_patches()

        # Alembic's default version_num width (VARCHAR(32)) is too short for
        # our human-readable revision IDs.
        await _ensure_alembic_version_capacity()

        # Clear pooled connections after potential DDL changes so asyncpg does not
        # reuse stale prepared plans.
        await engine.dispose()

        # Record Alembic heads directly in alembic_version.
        log("📝 Recording Alembic revision heads...")
        await _record_alembic_heads()
        log("✅ Alembic revision heads recorded!")

        # Initialize basic data
        log("🌸 Initializing basic data...")
        await initialize_basic_data()

        log("🎉 Database initialization complete!")
        return True

    except Exception as e:
        log(f"❌ Database initialization failed: {e}")
        return False


async def initialize_basic_data():
    """Initialize basic required data"""

    from src.bot.database import async_session_factory

    async with async_session_factory() as session:
        async with session.begin():
            # Initialize feature permissions
            log("  📋 Setting up feature permissions...")
            await setup_feature_permissions(session)

            # Initialize basic apploids
            log("  🎭 Setting up basic apploids...")
            await setup_basic_apploids(session)


async def setup_feature_permissions(session):
    """Set up default feature permissions"""

    from src.bot.models.features import FeaturePermission

    # Default permissions for all features
    default_permissions = [
        # Core moderation features
        ("moderation", "member", False),
        ("moderation", "admin", True),
        ("moderation", "captain", True),
        ("moderation", "commander", True),
        # Basic engagement features
        ("welcome", "member", True),
        ("welcome", "admin", True),
        ("welcome", "captain", True),
        ("welcome", "commander", True),
        ("user_info", "member", True),
        ("user_info", "admin", True),
        ("user_info", "captain", True),
        ("user_info", "commander", True),
        # Entertainment features
        ("flirting", "member", True),
        ("flirting", "admin", True),
        ("flirting", "captain", True),
        ("flirting", "commander", True),
        ("nico_moments", "member", True),
        ("nico_moments", "admin", True),
        ("nico_moments", "captain", True),
        ("nico_moments", "commander", True),
        # Bot friendship
        ("bot_friendship", "member", True),
        ("bot_friendship", "admin", True),
        ("bot_friendship", "captain", True),
        ("bot_friendship", "commander", True),
        # Point system
        ("points", "member", True),
        ("points", "admin", True),
        ("points", "captain", True),
        ("points", "commander", True),
        # Advanced features (admin+ only)
        ("filters", "member", False),
        ("filters", "admin", True),
        ("filters", "captain", True),
        ("filters", "commander", True),
        ("federation", "member", False),
        ("federation", "admin", True),
        ("federation", "captain", True),
        ("federation", "commander", True),
        ("feature_management", "member", False),
        ("feature_management", "admin", False),
        ("feature_management", "captain", True),
        ("feature_management", "commander", True),
    ]

    for feature_name, user_role, can_use in default_permissions:
        # Check if permission already exists
        result = await session.execute(
            text(
                "SELECT 1 FROM feature_permissions WHERE feature_name = :feature AND user_role = :role"
            ),
            {"feature": feature_name, "role": user_role},
        )
        existing = result.scalar_one_or_none()

        if not existing:
            permission = FeaturePermission(
                feature_name=feature_name, user_role=user_role, can_use=can_use
            )
            session.add(permission)


async def setup_basic_apploids(session):
    """Set up basic Nico Robin apploids"""

    from src.bot.models.points import Apploid

    basic_apploids = [
        {
            "apploid_name": "Robin Classic",
            "apploid_emoji": "🌸",
            "description": "Classic Nico Robin with gentle smile",
            "rarity": "common",
            "required_level": 1,
            "required_points": 0,
        },
        {
            "apploid_name": "Scholar Robin",
            "apploid_emoji": "📚",
            "description": "Robin with her glasses and books",
            "rarity": "common",
            "required_level": 1,
            "required_points": 50,
        },
        {
            "apploid_name": "Devil Child",
            "apploid_emoji": "😈",
            "description": "Robin's infamous Devil Child persona",
            "rarity": "rare",
            "required_level": 3,
            "required_points": 500,
        },
        {
            "apploid_name": "Archaeologist Robin",
            "apploid_emoji": "🗺️",
            "description": "Robin with ancient map and tools",
            "rarity": "rare",
            "required_level": 2,
            "required_points": 300,
        },
        {
            "apploid_name": "Blossom Robin",
            "apploid_emoji": "🌺",
            "description": "Robin surrounded by cherry blossoms",
            "rarity": "epic",
            "required_level": 5,
            "required_points": 2000,
        },
        {
            "apploid_name": "Ocean Robin",
            "apploid_emoji": "🌊",
            "description": "Robin by the sea with the Thousand Sunny",
            "rarity": "epic",
            "required_level": 4,
            "required_points": 1500,
        },
        {
            "apploid_name": "Nightingale Robin",
            "apploid_emoji": "🎶",
            "description": "Robin singing softly under the moon",
            "rarity": "epic",
            "required_level": 6,
            "required_points": 3500,
        },
        {
            "apploid_name": "Golden Robin",
            "apploid_emoji": "⭐",
            "description": "Robin glowing with golden light",
            "rarity": "legendary",
            "required_level": 8,
            "required_points": 10000,
        },
        {
            "apploid_name": "Poneglyph Robin",
            "apploid_emoji": "📜",
            "description": "Robin decoding ancient poneglyphs",
            "rarity": "legendary",
            "required_level": 7,
            "required_points": 8000,
        },
        {
            "apploid_name": "Angel Robin",
            "apploid_emoji": "👼",
            "description": "Robin with angelic wings and halo",
            "rarity": "legendary",
            "required_level": 10,
            "required_points": 25000,
        },
    ]

    for apploid_data in basic_apploids:
        # Check if apploid already exists
        result = await session.execute(
            text("SELECT 1 FROM apploids WHERE apploid_name = :name"),
            {"name": apploid_data["apploid_name"]},
        )
        existing = result.scalar_one_or_none()

        if not existing:
            apploid = Apploid(**apploid_data)
            session.add(apploid)


async def main():
    """Main initialization function"""

    log("🌸 Nico Robin Bot Database Initialization")
    log("=" * 50)

    success = await init_database()

    if success:
        log("\n✅ Database is ready!")
        log("🎯 You can now start the bot!")
        log("\nNext steps:")
        log("1. Update your .env file with database settings")
        log("2. Run the bot: python main.py")
        log("3. Test the new features!")
    else:
        log("\n❌ Database initialization failed!")
        log("🔧 Please check the error above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

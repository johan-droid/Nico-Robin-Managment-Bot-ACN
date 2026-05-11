#!/usr/bin/env python3
"""
Database Initialization Script
Runs the comprehensive migration and sets up the database
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from alembic.config import Config as AlembicConfig  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command as alembic_cmd  # noqa: E402
from database import engine  # noqa: E402
from models import Base  # noqa: E402


async def init_database():
    """Initialize the database with all tables"""

    print("🚀 Database Initialization")
    print("=" * 40)

    try:
        # Create all tables
        print("📋 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        print("✅ Database tables created successfully!")

        # Stamp alembic to head
        print("📝 Stamping Alembic to head...")
        try:
            cfg = AlembicConfig("alembic.ini")
            alembic_cmd.stamp(cfg, "head")
            print("✅ Alembic stamped successfully!")
        except Exception as e:
            print(f"⚠️  Alembic stamping failed (this is OK): {e}")

        # Initialize basic data
        print("🌸 Initializing basic data...")
        await initialize_basic_data()

        print("🎉 Database initialization complete!")
        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


async def initialize_basic_data():
    """Initialize basic required data"""

    from database import async_session_factory

    async with async_session_factory() as session:
        async with session.begin():
            # Initialize feature permissions
            print("  📋 Setting up feature permissions...")
            await setup_feature_permissions(session)

            # Initialize basic apploids
            print("  🎭 Setting up basic apploids...")
            await setup_basic_apploids(session)

            await session.commit()


async def setup_feature_permissions(session):
    """Set up default feature permissions"""

    from models.features import FeaturePermission

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
        existing = await session.execute(
            text(
                "SELECT 1 FROM feature_permissions WHERE feature_name = :feature AND user_role = :role"
            ),
            {"feature": feature_name, "role": user_role},
        ).scalar_one_or_none()

        if not existing:
            permission = FeaturePermission(
                feature_name=feature_name, user_role=user_role, can_use=can_use
            )
            session.add(permission)


async def setup_basic_apploids(session):
    """Set up basic Nico Robin apploids"""

    from models.points import Apploid

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
        existing = await session.execute(
            text("SELECT 1 FROM apploids WHERE apploid_name = :name"),
            {"name": apploid_data["apploid_name"]},
        ).scalar_one_or_none()

        if not existing:
            apploid = Apploid(**apploid_data)
            session.add(apploid)


async def main():
    """Main initialization function"""

    print("🌸 Nico Robin Bot Database Initialization")
    print("=" * 50)

    success = await init_database()

    if success:
        print("\n✅ Database is ready!")
        print("🎯 You can now start the bot!")
        print("\nNext steps:")
        print("1. Update your .env file with database settings")
        print("2. Run the bot: python main.py")
        print("3. Test the new features!")
    else:
        print("\n❌ Database initialization failed!")
        print("🔧 Please check the error above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

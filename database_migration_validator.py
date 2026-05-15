#!/usr/bin/env python3
"""
Database Migration Validator
Tests and validates the comprehensive feature migration
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import sqlalchemy as sa  # noqa: E402
from sqlalchemy import func, inspect, select, text  # noqa: E402

from database import engine  # noqa: E402


async def validate_migration():
    """Validate that all tables were created correctly"""

    print("🔍 Database Migration Validator")
    print("=" * 50)

    try:
        async with engine.begin() as conn:
            inspector = inspect(conn)

            # Get all table names
            tables = inspector.get_table_names()
            print(f"📊 Found {len(tables)} tables in database")

            # Expected tables from migration
            expected_tables = {
                # Core tables (should exist)
                "users",
                "groups",
                "group_members",
                # Feature management
                "feature_toggles",
                "feature_permissions",
                "feature_usage",
                "feature_logs",
                # Flirting system
                "flirting_attempts",
                "flirting_stats",
                "flirting_achievements",
                "flirting_relationships",
                "flirting_gifts",
                "flirting_preferences",
                # Bot friendship
                "bot_friendships",
                "bot_interactions",
                "bot_memories",
                "bot_gifts",
                "bot_conversations",
                "bot_emotions",
                # Point system
                "user_points",
                "point_transactions",
                "apploids",
                "user_apploids",
                "point_rewards",
                "point_redemptions",
                "point_streaks",
                "point_leaderboards",
                # Additional features
                "managed_channels",
                "member_profiles",
                # Existing tables
                "action_logs",
                "join_logs",
                "message_logs",
                "filters",
                "notes",
                "warns",
                "swear_words",
                "swear_violations",
                "loyalty_points",
                "loyalty_redemptions",
                "loyalty_rewards",
                "acn_activities",
                "acn_whitelist",
                "federations",
                "federation_admins",
                "federation_bans",
                "federation_groups",
                "event_audit_logs",
                "event_subscriptions",
                "realtime_events",
                "websocket_connections",
            }

            # Check for missing tables
            missing_tables = expected_tables - set(tables)
            extra_tables = set(tables) - expected_tables

            print("\n✅ Table Validation:")
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All expected tables found!")

            if extra_tables:
                print(f"ℹ️  Extra tables found: {extra_tables}")

            # Validate table structures
            print("\n🔧 Table Structure Validation:")

            # Check key tables have proper columns
            key_validations = [
                (
                    "feature_toggles",
                    ["toggle_id", "group_id", "feature_name", "is_enabled"],
                ),
                ("flirting_attempts", ["attempt_id", "user_id", "group_id", "success"]),
                (
                    "bot_friendships",
                    ["friendship_id", "companion_bot_id", "friendship_level"],
                ),
                ("user_points", ["points_id", "user_id", "group_id", "current_points"]),
                ("apploids", ["apploid_id", "apploid_name", "rarity"]),
                (
                    "member_profiles",
                    ["profile_id", "user_id", "group_id", "total_messages"],
                ),
            ]

            for table_name, required_columns in key_validations:
                if table_name in tables:
                    columns = [col["name"] for col in inspector.get_columns(table_name)]
                    missing_columns = set(required_columns) - set(columns)

                    if missing_columns:
                        print(f"❌ {table_name}: Missing columns {missing_columns}")
                        return False
                    else:
                        print(f"✅ {table_name}: Structure OK")
                else:
                    print(f"❌ {table_name}: Table not found")
                    return False

            # Check foreign key constraints
            print("\n🔗 Foreign Key Validation:")

            fk_validations = [
                ("feature_toggles", ["groups"], ["group_id"]),
                ("flirting_attempts", ["users", "groups"], ["user_id", "group_id"]),
                ("bot_friendships", ["groups"], ["group_id"]),
                ("user_points", ["users", "groups"], ["user_id", "group_id"]),
                (
                    "user_apploids",
                    ["users", "groups", "apploids"],
                    ["user_id", "group_id", "apploid_id"],
                ),
                ("member_profiles", ["users", "groups"], ["user_id", "group_id"]),
            ]

            for table_name, expected_refs, _fk_columns in fk_validations:
                if table_name in tables:
                    fks = inspector.get_foreign_keys(table_name)
                    ref_tables = {fk["referred_table"] for fk in fks}
                    {fk["constrained_columns"][0] for fk in fks}

                    if set(expected_refs) <= ref_tables:
                        print(f"✅ {table_name}: Foreign keys OK")
                    else:
                        print(f"❌ {table_name}: Missing references to {expected_refs}")
                        return False
                else:
                    print(f"❌ {table_name}: Table not found")
                    return False

            # Check indexes
            print("\n📈 Index Validation:")

            index_validations = [
                ("feature_toggles", ["ix_feature_toggles_group_id"]),
                ("user_points", ["ix_user_points_user_id", "ix_user_points_group_id"]),
                ("flirting_attempts", ["ix_flirting_attempts_user_id"]),
                ("apploids", ["ix_apploids_rarity"]),
            ]

            for table_name, expected_indexes in index_validations:
                if table_name in tables:
                    indexes = inspector.get_indexes(table_name)
                    index_names = {idx["name"] for idx in indexes}

                    missing_indexes = set(expected_indexes) - index_names
                    if missing_indexes:
                        print(f"⚠️  {table_name}: Missing indexes {missing_indexes}")
                    else:
                        print(f"✅ {table_name}: Indexes OK")

            # Test basic data insertion
            print("\n🧪 Data Insertion Test:")

            try:
                # Test inserting into apploids table
                await conn.execute(
                    text(
                        """
                    INSERT INTO apploids (apploid_name, apploid_emoji, description, rarity, required_level, required_points)
                    VALUES ('Test Apploid', '🧪', 'Test apploid for validation', 'common', 1, 0)
                    ON CONFLICT (apploid_name) DO NOTHING
                """
                    )
                )

                # Test inserting into feature_permissions
                await conn.execute(
                    text(
                        """
                    INSERT INTO feature_permissions (feature_name, user_role, can_use)
                    VALUES ('test_feature', 'member', true)
                    ON CONFLICT (feature_name, user_role) DO NOTHING
                """
                    )
                )

                print("✅ Basic data insertion works")

                # Clean up test data
                await conn.execute(
                    text("DELETE FROM apploids WHERE apploid_name = 'Test Apploid'")
                )
                await conn.execute(
                    text(
                        "DELETE FROM feature_permissions WHERE feature_name = 'test_feature'"
                    )
                )

            except Exception as e:
                print(f"❌ Data insertion test failed: {e}")
                return False

            print("\n🎉 Migration Validation Complete!")
            print("✅ All validations passed successfully!")
            return True

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return False


async def show_database_info():
    """Show current database information"""

    print("\n📊 Database Information:")
    print("-" * 30)

    try:
        async with engine.begin() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()

            print(f"Total Tables: {len(tables)}")
            print("\nTables by Category:")

            # Group tables by category
            categories = {
                "Core": ["users", "groups", "group_members"],
                "Feature Management": [
                    "feature_toggles",
                    "feature_permissions",
                    "feature_usage",
                    "feature_logs",
                ],
                "Flirting": [t for t in tables if t.startswith("flirting")],
                "Bot Friendship": [t for t in tables if t.startswith("bot")],
                "Point System": [
                    t
                    for t in tables
                    if "point" in t or t in ["apploids", "user_apploids"]
                ],
                "Other": [],
            }

            for category, category_tables in categories.items():
                if category_tables:
                    existing = [t for t in category_tables if t in tables]
                    if existing:
                        print(f"  {category}: {len(existing)} tables")
                        for table in existing:
                            columns = len(inspector.get_columns(table))
                            print(f"    - {table} ({columns} columns)")

            # Show table counts
            total_rows = 0
            for table_name in tables:
                try:
                    # Use SQLAlchemy expression language to prevent SQL injection
                    # although table names come from inspector, this is safer and follows best practices
                    stmt = select(func.count()).select_from(sa.table(table_name))
                    result = await conn.execute(stmt)
                    count = result.scalar()
                    total_rows += count
                    if count > 0:
                        print(f"  {table_name}: {count:,} rows")
                except Exception:
                    pass  # Skip tables that can't be counted

            print(f"\nTotal Rows: {total_rows:,}")

    except Exception as e:
        print(f"❌ Failed to get database info: {e}")


async def main():
    """Main validation function"""

    print("🚀 Starting Database Migration Validation")
    print("=" * 60)

    # Run validation
    success = await validate_migration()

    # Show database info
    await show_database_info()

    if success:
        print("\n✅ Migration validation completed successfully!")
        print("🎯 Database is ready for use!")
    else:
        print("\n❌ Migration validation failed!")
        print("🔧 Please check the errors above and fix them.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

with open("alembic/versions/2024_01_10_comprehensive_feature_migration.py") as f:
    content = f.read()

# Fix the syntax error by removing the incorrect kwargs
bad_str = """        task_track_started=True,
        broker_connection_retry_on_startup=True,"""

content = content.replace(bad_str, "")

with open("alembic/versions/2024_01_10_comprehensive_feature_migration.py", "w") as f:
    f.write(content)

with open("main.py") as f:
    content = f.read()

content = content.replace("raise SystemExit(1)", "raise SystemExit(1) from None")

with open("main.py", "w") as f:
    f.write(content)

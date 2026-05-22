import os
import re


def update_imports_in_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    modules = [
        "bot",
        "models",
        "services",
        "utils",
        "database",
        "config",
        "gateway",
        "client",
        "tasks",
        "alembic",
    ]

    original_content = content
    for module in modules:
        content = re.sub(
            r"^from " + module + r"\b",
            f"from src.bot.{module}",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^import " + module + r"\b",
            f"import src.bot.{module}",
            content,
            flags=re.MULTILINE,
        )

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated imports in {filepath}")


for root, dirs, files in os.walk("."):
    if ".git" in root or "archive" in root:
        continue
    for file in files:
        if file.endswith(".py") and file not in [
            "update_imports.py",
            "categorize.py",
            "fix_admin_welcome.py",
        ]:
            filepath = os.path.join(root, file)
            update_imports_in_file(filepath)

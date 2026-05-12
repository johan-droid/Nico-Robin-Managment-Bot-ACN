with open("tests/test_config.py") as f:
    content = f.read()

content = content.replace(
    'assert settings.database_url.startswith("postgresql+asyncpg://")',
    'assert settings.async_database_url.startswith("postgresql+asyncpg://")',
)

with open("tests/test_config.py", "w") as f:
    f.write(content)

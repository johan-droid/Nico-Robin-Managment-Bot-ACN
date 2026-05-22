import re

with open("src/bot/bot/plugins/admin.py", "r") as f:
    content = f.read()

content = re.sub(
    r"from typing import (.+)",
    r"from typing import \1, Coroutine, Any",
    content,
    count=1,
)

with open("src/bot/bot/plugins/admin.py", "w") as f:
    f.write(content)

with open("src/bot/bot/plugins/welcome.py", "r") as f:
    content = f.read()

content = re.sub(
    r"from telegram\.error import (.+)",
    r"from telegram.error import \1, Forbidden",
    content,
    count=1,
)
content = re.sub(
    r"from telegram import (.+)",
    r"from telegram import \1, InlineKeyboardMarkup, InlineKeyboardButton",
    content,
    count=1,
)

with open("src/bot/bot/plugins/welcome.py", "w") as f:
    f.write(content)

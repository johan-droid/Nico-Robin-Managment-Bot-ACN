import re

with open("src/bot/bot/plugins/admin.py", "r") as f:
    content = f.read()

content = re.sub(
    r"from typing import Literal, cast",
    "from typing import Literal, cast, Coroutine, Any",
    content,
)

with open("src/bot/bot/plugins/admin.py", "w") as f:
    f.write(content)


with open("src/bot/bot/plugins/welcome.py", "r") as f:
    content = f.read()

content = re.sub(
    r"from telegram.error import BadRequest",
    "from telegram.error import BadRequest, Forbidden",
    content,
)
content = re.sub(
    r"from telegram import ChatMember, Update",
    "from telegram import ChatMember, Update, InlineKeyboardMarkup, InlineKeyboardButton",
    content,
)

with open("src/bot/bot/plugins/welcome.py", "w") as f:
    f.write(content)

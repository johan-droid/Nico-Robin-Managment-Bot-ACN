with open("src/bot/bot/plugins/admin.py", "r") as f:
    content = f.read()

content = content.replace(
    "from typing import Literal, cast",
    "from typing import Literal, cast, Coroutine, Any",
)
with open("src/bot/bot/plugins/admin.py", "w") as f:
    f.write(content)


with open("src/bot/bot/plugins/welcome.py", "r") as f:
    content = f.read()

content = content.replace(
    "from telegram.error import BadRequest",
    "from telegram.error import BadRequest, Forbidden",
)
content = content.replace(
    "from telegram import ChatMember, Update",
    "from telegram import ChatMember, Update, InlineKeyboardMarkup, InlineKeyboardButton",
)
with open("src/bot/bot/plugins/welcome.py", "w") as f:
    f.write(content)

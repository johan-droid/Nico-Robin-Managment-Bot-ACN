with open("src/bot/bot/plugins/admin.py", "r") as f:
    content = f.read()

content = content.replace(
    "from typing import Literal, cast",
    "from typing import Literal, cast, Coroutine, Any",
)

with open("src/bot/bot/plugins/admin.py", "w") as f:
    f.write(content)

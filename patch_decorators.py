import re

with open("src/bot/utils/decorators.py", "r") as f:
    content = f.read()

# Fix require_captain_commander
old_func = """def require_captain_commander(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat = getattr(update, "effective_chat", None)
        if user is None:
            return
        if chat is not None:
            allowed = await ACNService.is_admin_or_owner(user.id, chat, context)
        else:
            allowed = await ACNService.is_captain(
                user.id
            ) or await ACNService.is_commander(user.id)

        if allowed:"""

new_func = """def require_captain_commander(func: Handler) -> Handler:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            return

        allowed = await ACNService.is_captain(user.id) or await ACNService.is_commander(user.id)

        if allowed:"""

content = content.replace(old_func, new_func)

with open("src/bot/utils/decorators.py", "w") as f:
    f.write(content)

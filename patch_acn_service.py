import re

with open("src/bot/services/acn_service.py", "r") as f:
    content = f.read()

old_func = """    @staticmethod
    async def is_commander(user_id: int) -> bool:
        \"\"\"Check if user is a commander\"\"\"
        return user_id in ACNService.COMMANDER_IDS"""

new_func = """    @staticmethod
    async def is_commander(user_id: int) -> bool:
        \"\"\"Check if user is a commander\"\"\"
        if user_id in ACNService.COMMANDER_IDS:
            return True
        return await ACNService.get_user_role(user_id) == "commander\""""

content = content.replace(old_func, new_func)

with open("src/bot/services/acn_service.py", "w") as f:
    f.write(content)

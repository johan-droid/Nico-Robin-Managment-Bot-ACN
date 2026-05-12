with open("bot/dispatcher.py") as f:
    content = f.read()

content = content.replace(
    '    "bot.plugins.profile",', '    "bot.plugins.profile",\n    "bot.plugins.locks",'
)

with open("bot/dispatcher.py", "w") as f:
    f.write(content)

import re

with open("src/bot/bot/handlers_list.py", "r") as f:
    content = f.read()

# Imports
if "from src.bot.bot.plugins import admin as admin_plugin" not in content:
    content = content.replace("from src.bot.bot.plugins import acn_broadcast", "from src.bot.bot.plugins import admin as admin_plugin\nfrom src.bot.bot.plugins import feature_management as feature_management_plugin\nfrom src.bot.bot.plugins import acn_broadcast")

# Replacements
content = content.replace('CommandBinding("management", welcome_plugin.help_cmd', 'CommandBinding("management", feature_management_plugin.management_help')
content = content.replace('CommandBinding("features", welcome_plugin.help_cmd', 'CommandBinding("features", feature_management_plugin.features')

content = content.replace('CommandBinding("ban", welcome_plugin.help_cmd', 'CommandBinding("ban", admin_plugin.ban')
content = content.replace('CommandBinding("unban", welcome_plugin.help_cmd', 'CommandBinding("unban", admin_plugin.unban')
content = content.replace('CommandBinding("kick", welcome_plugin.help_cmd', 'CommandBinding("kick", admin_plugin.kick')
content = content.replace('CommandBinding("mute", welcome_plugin.help_cmd', 'CommandBinding("mute", admin_plugin.mute')
content = content.replace('CommandBinding("warn", welcome_plugin.help_cmd', 'CommandBinding("warn", admin_plugin.warn')

with open("src/bot/bot/handlers_list.py", "w") as f:
    f.write(content)

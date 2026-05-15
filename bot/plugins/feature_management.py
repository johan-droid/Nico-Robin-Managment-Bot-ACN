from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database import async_session_factory
from models.features import FeatureToggle
from services.acn_service import ACNService, acn_only, captain_commander_only
from services.feature_service import FeatureService
from utils.formatters import telegram_user_label


async def management_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the management command reference and use cases."""
    msg = update.effective_message
    if msg is None:
        return

    del context
    response = (
        "🌸 **Anime Crew Network Management Guide**\n\n"
        "**Moderation & Protection**\n"
        "Use these when you need to control spam, abuse, or member behavior.\n"
        "• `/toggleai on/off` - turn AI moderation on or off\n"
        "• `/ban`, `/unban`, `/kick` - remove or restore members\n"
        "• `/mute`, `/unmute` - silence or restore chat access\n"
        "• `/warn`, `/warns`, `/resetwarn` - issue and review warnings\n"
        "• `/slowmode` - limit message flooding\n\n"
        "**Content Management**\n"
        "Use these to keep group messages clean and organized.\n"
        "• `/del` - delete a replied message\n"
        "• `/purge` - remove a batch of messages\n"
        "• `/pin` - pin important announcements\n"
        "• `/filter`, `/stop`, `/filters`, `/filteraction` - manage word filters\n\n"
        "**Welcome & Rules**\n"
        "Use these to control onboarding and group guidelines.\n"
        "• `/setwelcome`, `/resetwelcome`, `/welcome on/off` - welcome messages\n"
        "• `/setfarewell`, `/farewell on/off` - goodbye messages\n"
        "• `/cleanwelcome on/off` - auto-remove welcome clutter\n"
        "• `/setrules`, `/rules` - define and show group rules\n"
        "• `/welcometest` - preview the current welcome text\n\n"
        "**Group Info & Notes**\n"
        "Use these to inspect the group and keep useful records.\n"
        "• `/stats` - group activity summary\n"
        "• `/id` - show chat or user id\n"
        "• `/whois`, `/info` - inspect a member\n"
        "• `/save`, `/get`, `/notes`, `/clear` - manage note pages\n\n"
        "**Settings & Controls**\n"
        "Use these to tune the group behavior.\n"
        "• `/setlocale` - change language\n"
        "• `/setwarnlimit`, `/setwarnaction` - change warning policy\n"
        "• `/setflood`, `/setfloodmode`, `/flood on/off` - flood protection\n"
        "• `/captcha on/off` - new member verification\n\n"
        "**Feature Management**\n"
        "Use these when captain/commander needs to switch bot modules.\n"
        "• `/features` - list every feature\n"
        "• `/enable`, `/disable`, `/toggle` - change a feature\n"
        "• `/feature_info` - explain a feature\n"
        "• `/feature_logs`, `/feature_stats` - inspect usage and history\n"
        "• `/my_features` - show what your role can use\n"
        "• `/enable_category`, `/disable_category`, `/reset_features confirm` - bulk control\n\n"
        "If you want, I can also make this guide available as `/help` in groups."
    )
    await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def enable_feature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable a bot feature (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🌸 Usage: `/enable <feature_name> [reason]\n"
            "Use `/features` to see all available features."
        )
        return

    feature_name = args[0].lower()
    reason = " ".join(args[1:]) if len(args) > 1 else None

    # Toggle feature
    success, message = await FeatureService.toggle_feature(
        group_id=chat.id,
        feature_name=feature_name,
        enabled=True,
        user_id=update.effective_user.id if update.effective_user else None,
        reason=reason,
    )

    if success:
        await msg.reply_text(f"✅ {message}")
    else:
        await msg.reply_text(f"❌ {message}")


@captain_commander_only
async def disable_feature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable a bot feature (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🌸 Usage: `/disable <feature_name> [reason]\n"
            "Use `/features` to see all available features."
        )
        return

    feature_name = args[0].lower()
    reason = " ".join(args[1:]) if len(args) > 1 else None

    # Toggle feature
    success, message = await FeatureService.toggle_feature(
        group_id=chat.id,
        feature_name=feature_name,
        enabled=False,
        user_id=update.effective_user.id if update.effective_user else None,
        reason=reason,
    )

    if success:
        await msg.reply_text(f"✅ {message}")
    else:
        await msg.reply_text(f"❌ {message}")


@captain_commander_only
async def toggle_feature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle a bot feature on/off (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🌸 Usage: `/toggle <feature_name> [reason]\n"
            "Use `/features` to see all available features."
        )
        return

    feature_name = args[0].lower()
    reason = " ".join(args[1:]) if len(args) > 1 else None

    # Check current status
    current_status = await FeatureService.is_feature_enabled(chat.id, feature_name)

    # Toggle to opposite
    success, message = await FeatureService.toggle_feature(
        group_id=chat.id,
        feature_name=feature_name,
        enabled=not current_status,
        user_id=update.effective_user.id if update.effective_user else None,
        reason=reason,
    )

    if success:
        status_emoji = "✅" if not current_status else "❌"
        await msg.reply_text(f"{status_emoji} {message}")
    else:
        await msg.reply_text(f"❌ {message}")


@captain_commander_only
async def features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all available features and their status (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    # Get feature status
    feature_status = await FeatureService.get_feature_status(chat.id)

    # Group by category
    categories = {}
    for feature_name, status in feature_status.items():
        category = status["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append((feature_name, status))

    # Format response
    response = f"🌸 **Bot Features for {chat.title}**\n\n"

    category_emojis = {
        "moderation": "🛡️",
        "ai": "🤖",
        "engagement": "👋",
        "entertainment": "🎮",
        "utility": "🛠️",
        "federation": "🌐",
        "acn": "⚓",
        "advanced": "🚀",
        "security": "🔒",
    }

    for category, features in categories.items():
        emoji = category_emojis.get(category, "📋")
        response += f"{emoji} **{category.title()} Features:**\n"

        for feature_name, status in sorted(features):
            status_emoji = "✅" if status["is_enabled"] else "❌"
            name = status["name"]
            response += f"  {status_emoji} `{feature_name}` - {name}\n"

        response += "\n"

    response += "💡 **Use:** `/enable <feature>`, `/disable <feature>`, or `/toggle <feature>`\n"
    response += "👥 **Only captains and commanders can manage features**"

    await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def feature_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed information about a specific feature"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text(
            "🌸 Usage: `/feature_info <feature_name>\n"
            "Use `/features` to see all available features."
        )
        return

    feature_name = args[0].lower()

    # Get feature status
    feature_status = await FeatureService.get_feature_status(chat.id)

    if feature_name not in feature_status:
        await msg.reply_text(f"❌ Feature '{feature_name}' not found.")
        return

    status = feature_status[feature_name]
    all_features = FeatureService.get_all_features()
    feature_info = all_features[feature_name]

    # Format detailed response
    response = f"🌸 **Feature Details: {status['name']}**\n\n"
    response += f"📝 **Description:** {status['description']}\n"
    response += f"📂 **Category:** {status['category'].title()}\n"
    response += (
        f"🔧 **Status:** {'✅ Enabled' if status['is_enabled'] else '❌ Disabled'}\n"
    )
    response += f"🎯 **Default:** {'✅ Enabled' if status['default_enabled'] else '❌ Disabled'}\n"

    if status["toggled_by"]:
        response += f"👤 **Last Modified By:** User {status['toggled_by']}\n"

    if status["toggle_reason"]:
        response += f"📝 **Reason:** {status['toggle_reason']}\n"

    if status["updated_at"]:
        response += f"🕐 **Last Updated:** {status['updated_at']}\n"

    response += f"👥 **Required Roles:** {', '.join(feature_info['permissions'])}\n"
    response += f"🔒 **Owner Only:** {'Yes' if feature_info['owner_only'] else 'No'}\n"

    await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def feature_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show feature toggle logs (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    feature_name = args[0].lower() if args else None
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20

    # Get logs
    logs = await FeatureService.get_feature_logs(chat.id, feature_name, limit)

    if not logs:
        await msg.reply_text("📋 No feature logs found.")
        return

    response = "📋 **Feature Toggle Logs**\n\n"

    for log in logs:
        action_emoji = "✅" if log["action"] == "enabled" else "❌"
        response += (
            f"{action_emoji} **{log['feature_name']}** - {log['action'].title()}\n"
        )
        response += f"   👤 User {log['user_id']} | 📝 {log['reason'] or 'No reason'}\n"
        response += f"   🕐 {log['created_at'][:19]}\n\n"

    await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def feature_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show feature usage statistics (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    feature_name = args[0].lower() if args else None

    # Get usage stats
    stats = await FeatureService.get_feature_usage_stats(chat.id, feature_name)

    if not stats:
        await msg.reply_text("📊 No feature usage statistics found.")
        return

    response = "📊 **Feature Usage Statistics**\n\n"

    # Group by feature
    feature_stats = {}
    for stat in stats:
        feature = stat["feature_name"]
        if feature not in feature_stats:
            feature_stats[feature] = []
        feature_stats[feature].append(stat)

    for feature, feature_data in feature_stats.items():
        total_usage = sum(item["usage_count"] for item in feature_data)
        response += f"📈 **{feature}** - Total Usage: {total_usage}\n"

        # Show top users
        top_users = sorted(feature_data, key=lambda x: x["usage_count"], reverse=True)[
            :3
        ]
        for user_stat in top_users:
            response += (
                f"   👤 User {user_stat['user_id']}: {user_stat['usage_count']} uses\n"
            )

        response += "\n"

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def my_features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show features available to current user"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Get user role
    user_role = await ACNService.get_user_role(user.id)

    # Get all features
    all_features = FeatureService.get_all_features()

    # Filter features user can access
    accessible_features = []
    for feature_name, feature_info in all_features.items():
        if user_role in feature_info["permissions"]:
            is_enabled = await FeatureService.is_feature_enabled(chat.id, feature_name)
            accessible_features.append((feature_name, feature_info, is_enabled))

    # Group by category
    categories = {}
    for feature_name, feature_info, is_enabled in accessible_features:
        category = feature_info["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append((feature_name, feature_info, is_enabled))

    # Format response
    response = f"🌸 **Available Features for {telegram_user_label(user)}**\n"
    response += f"👤 **Role:** {user_role.title()}\n\n"

    category_emojis = {
        "moderation": "🛡️",
        "ai": "🤖",
        "engagement": "👋",
        "entertainment": "🎮",
        "utility": "🛠️",
        "federation": "🌐",
        "acn": "⚓",
        "advanced": "🚀",
        "security": "🔒",
    }

    for category, features in categories.items():
        emoji = category_emojis.get(category, "📋")
        response += f"{emoji} **{category.title()}:**\n"

        for feature_name, feature_info, is_enabled in sorted(features):
            status_emoji = "✅" if is_enabled else "❌"
            response += f"  {status_emoji} `{feature_name}` - {feature_info['name']}\n"

        response += "\n"

    await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def reset_features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset all features to default settings (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    # Confirm action
    args = context.args or []
    if args and args[0].lower() == "confirm":
        # Reset all features to default
        async with async_session_factory() as session:
            from sqlalchemy import delete

            # Delete all feature toggles for this group
            await session.execute(
                delete(FeatureToggle).where(FeatureToggle.group_id == chat.id)
            )
            await session.commit()

        await msg.reply_text(
            "✅ **All features reset to default settings!**\n\n"
            "Use `/features` to see current status."
        )
    else:
        await msg.reply_text(
            "⚠️ **This will reset ALL features to their default settings.**\n\n"
            "To confirm, use: `/reset_features confirm`\n\n"
            "This action cannot be undone!"
        )


@captain_commander_only
async def enable_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable all features in a category (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        categories = FeatureService.get_categories()
        await msg.reply_text(
            f"🌸 Usage: `/enable_category <category>\n\n"
            f"**Available categories:** {', '.join(categories)}"
        )
        return

    category = args[0].lower()
    all_features = FeatureService.get_all_features()

    # Get features in this category
    category_features = [
        name for name, info in all_features.items() if info["category"] == category
    ]

    if not category_features:
        await msg.reply_text(f"❌ Category '{category}' not found.")
        return

    # Enable all features in category
    enabled_count = 0
    failed_count = 0

    for feature_name in category_features:
        success, _ = await FeatureService.toggle_feature(
            group_id=chat.id,
            feature_name=feature_name,
            enabled=True,
            user_id=update.effective_user.id if update.effective_user else None,
            reason=f"Enabled all {category} features",
        )

        if success:
            enabled_count += 1
        else:
            failed_count += 1

    await msg.reply_text(
        f"✅ **Category {category.title()} Updated**\n\n"
        f"✅ Enabled: {enabled_count} features\n"
        f"❌ Failed: {failed_count} features"
    )


@captain_commander_only
async def disable_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable all features in a category (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    args = context.args or []
    if len(args) < 1:
        categories = FeatureService.get_categories()
        await msg.reply_text(
            f"🌸 Usage: `/disable_category <category>\n\n"
            f"**Available categories:** {', '.join(categories)}"
        )
        return

    category = args[0].lower()
    all_features = FeatureService.get_all_features()

    # Get features in this category
    category_features = [
        name for name, info in all_features.items() if info["category"] == category
    ]

    if not category_features:
        await msg.reply_text(f"❌ Category '{category}' not found.")
        return

    # Disable all features in category
    disabled_count = 0
    failed_count = 0

    for feature_name in category_features:
        success, _ = await FeatureService.toggle_feature(
            group_id=chat.id,
            feature_name=feature_name,
            enabled=False,
            user_id=update.effective_user.id if update.effective_user else None,
            reason=f"Disabled all {category} features",
        )

        if success:
            disabled_count += 1
        else:
            failed_count += 1

    await msg.reply_text(
        f"✅ **Category {category.title()} Updated**\n\n"
        f"✅ Disabled: {disabled_count} features\n"
        f"❌ Failed: {failed_count} features"
    )


def register(app) -> None:
    """Register feature management commands"""
    app.add_handler(CommandHandler("management", management_help))
    app.add_handler(CommandHandler("enable", enable_feature))
    app.add_handler(CommandHandler("disable", disable_feature))
    app.add_handler(CommandHandler("toggle", toggle_feature))
    app.add_handler(CommandHandler("features", features))
    app.add_handler(CommandHandler("feature_info", feature_info))
    app.add_handler(CommandHandler("feature_logs", feature_logs))
    app.add_handler(CommandHandler("feature_stats", feature_stats))
    app.add_handler(CommandHandler("my_features", my_features))
    app.add_handler(CommandHandler("reset_features", reset_features))
    app.add_handler(CommandHandler("enable_category", enable_category))
    app.add_handler(CommandHandler("disable_category", disable_category))

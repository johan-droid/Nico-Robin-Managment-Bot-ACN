from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler
from telegram.ext import filters as tg_filters

from services.acn_service import acn_only, captain_commander_only
from services.broadcast_service import (
    BroadcastService,
    add_broadcast_channel,
    add_main_group,
    get_broadcast_channels,
    remove_broadcast_channel,
)


@captain_commander_only
async def add_broadcast_channel_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Add channel to ACN broadcast whitelist (Captain/Commander only)"""
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if len(args) < 2:
        await msg.reply_text(
            "🌸 Usage: `/addbroadcast <channel_id> <channel_type> [channel_name]\n"
            "Types: announcement, update, news, event, general"
        )
        return

    try:
        channel_id = int(args[0])
        channel_type = args[1].lower()
        channel_name = " ".join(args[2:]) if len(args) > 2 else f"Channel {channel_id}"

        if channel_type not in ["announcement", "update", "news", "event", "general"]:
            await msg.reply_text(
                "🌸 Invalid channel type. Use: announcement, update, news, event, or general"
            )
            return

        # Add channel to whitelist
        success = await add_broadcast_channel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=channel_type,
            added_by=update.effective_user.id if update.effective_user else None,
        )

        if success:
            await msg.reply_text(
                f"🌸 **Broadcast Channel Added!**\n\n"
                f"✅ {channel_name}\n"
                f"📺 Channel ID: {channel_id}\n"
                f"📋 Type: {channel_type}\n"
                f"🎯 Posts from this channel will be broadcast to all main ACN groups."
            )
        else:
            await msg.reply_text(
                "🌸 Failed to add broadcast channel. Please check the channel ID."
            )

    except ValueError:
        await msg.reply_text(
            "🌸 Invalid channel ID. Please provide a valid numeric channel ID."
        )
    except Exception as e:
        await msg.reply_text(f"🌸 Error: {str(e)}")


@captain_commander_only
async def remove_broadcast_channel_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove channel from ACN broadcast whitelist (Captain/Commander only)"""
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    if len(args) < 1:
        await msg.reply_text("🌸 Usage: `/removebroadcast <channel_id>`")
        return

    try:
        channel_id = int(args[0])

        # Remove channel from whitelist
        success = await remove_broadcast_channel(channel_id)

        if success:
            await msg.reply_text(
                f"🌸 **Broadcast Channel Removed!**\n\n"
                f"✅ Channel {channel_id} will no longer broadcast to ACN groups."
            )
        else:
            await msg.reply_text("🌸 Channel not found in broadcast whitelist.")

    except ValueError:
        await msg.reply_text(
            "🌸 Invalid channel ID. Please provide a valid numeric channel ID."
        )
    except Exception as e:
        await msg.reply_text(f"🌸 Error: {str(e)}")


@captain_commander_only
async def add_main_group_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Add group as main ACN group for broadcasts (Captain/Commander only)"""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    # Add current group as main group
    success = await add_main_group(
        group_id=chat.id,
        group_name=chat.title or f"Group {chat.id}",
        added_by=update.effective_user.id if update.effective_user else None,
    )

    if success:
        await msg.reply_text(
            f"🌸 **Main ACN Group Added!**\n\n"
            f"✅ {chat.title}\n"
            f"🎯 This group will receive broadcasts from all ACN channels."
        )
    else:
        await msg.reply_text("🌸 Failed to add main group. Please try again.")


@acn_only
async def list_broadcast_channels(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """List all ACN broadcast channels"""
    msg = update.effective_message
    if msg is None:
        return

    channels = await get_broadcast_channels()

    if not channels:
        await msg.reply_text("🌸 No broadcast channels configured.")
        return

    # Group channels by type
    type_groups = {}
    for channel in channels:
        channel_type = channel["channel_type"]
        if channel_type not in type_groups:
            type_groups[channel_type] = []
        type_groups[channel_type].append(channel)

    # Format response
    response = "🌸 **ACN Broadcast Channels**\n\n"

    type_emojis = {
        "announcement": "📢",
        "update": "🔄",
        "news": "📰",
        "event": "🎉",
        "general": "📋",
    }

    for channel_type, channels_list in type_groups.items():
        emoji = type_emojis.get(channel_type, "📋")
        response += f"{emoji} **{channel_type.title()} Channels:**\n"

        for channel in channels_list:
            response += f"• {channel['channel_name']} (ID: {channel['channel_id']})\n"

        response += "\n"

    response += (
        f"🎯 **Total:** {len(channels)} channels broadcasting to main ACN groups."
    )

    await msg.reply_text(response, parse_mode="Markdown")


@acn_only
async def broadcast_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show broadcast system status"""
    msg = update.effective_message
    if msg is None:
        return

    # Get statistics
    channels = await get_broadcast_channels()
    main_groups = await BroadcastService.get_main_acn_groups()

    # Count by type
    type_counts = {}
    for channel in channels:
        channel_type = channel["channel_type"]
        type_counts[channel_type] = type_counts.get(channel_type, 0) + 1

    response = "🌸 **ACN Broadcast System Status**\n\n"
    response += f"📺 **Active Channels:** {len(channels)}\n"
    response += f"👥 **Main Groups:** {len(main_groups)}\n\n"

    if type_counts:
        response += "📋 **Channel Types:**\n"
        for channel_type, count in type_counts.items():
            emoji = {
                "announcement": "📢",
                "update": "🔄",
                "news": "📰",
                "event": "🎉",
                "general": "📋",
            }.get(channel_type, "📋")
            response += f"• {emoji} {channel_type.title()}: {count}\n"

        response += "\n"

    response += "🎯 **System Status:** ✅ Active\n"
    response += "⚡ **Auto-Broadcast:** Enabled\n"
    response += "🌸 **Last Update:** Real-time monitoring"

    await msg.reply_text(response, parse_mode="Markdown")


@captain_commander_only
async def test_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send test broadcast to main groups (Captain/Commander only)"""
    msg = update.effective_message
    if msg is None:
        return

    args = context.args or []
    test_message = (
        " ".join(args) if args else "This is a test broadcast from ACN leadership."
    )

    # Create test message
    test_text = "🧪 **TEST BROADCAST**\n\n"
    test_text += "📺 **Source:** ACN Test System\n"
    test_text += f"🕐 **Time:** {context.bot_data.get('test_time', 'Now')}\n\n"
    test_text += f"📝 **Message:**\n{test_message}\n\n"
    test_text += "—\n🌸 *Test broadcast by Nico Robin Bot*\n"
    test_text += "⚓ *Anime Crew Network*"

    # Get main groups
    main_groups = await BroadcastService.get_main_acn_groups()

    if not main_groups:
        await msg.reply_text("🌸 No main ACN groups configured for broadcasting.")
        return

    # Send test broadcast
    successful = 0
    failed = 0

    for group_id in main_groups:
        try:
            await context.bot.send_message(
                chat_id=group_id, text=test_text, parse_mode="Markdown"
            )
            successful += 1
        except Exception as e:
            failed += 1
            print(f"Failed to send test broadcast to {group_id}: {e}")

    await msg.reply_text(
        f"🌸 **Test Broadcast Completed!**\n\n"
        f"✅ **Successful:** {successful} groups\n"
        f"❌ **Failed:** {failed} groups\n"
        f"📊 **Total:** {len(main_groups)} groups"
    )


@acn_only
async def broadcast_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show broadcast system help"""
    msg = update.effective_message
    if msg is None:
        return

    help_text = """
🌸 **ACN Broadcast System Help**

**What it does:**
- Monitors ACN-related Telegram channels
- Automatically broadcasts posts to main ACN groups
- Professional formatting with timestamps and source info

**Captain/Commander Commands:**
• `/addbroadcast <channel_id> <type> [name]` - Add broadcast channel
• `/removebroadcast <channel_id>` - Remove broadcast channel
• `/addmaingroup` - Add current group as main broadcast group
• `/testbroadcast [message]` - Send test broadcast

**All ACN Members:**
• `/broadcastchannels` - List all broadcast channels
• `/broadcaststatus` - Show system status
• `/broadcasthelp` - Show this help

**Channel Types:**
• `announcement` - Official announcements 📢
• `update` - Network updates 🔄
• `news` - ACN news 📰
• `event` - ACN events 🎉
• `general` - General broadcasts 📋

**How it works:**
1. Add channels to broadcast whitelist
2. Add main groups to receive broadcasts
3. Posts in channels automatically broadcast to groups
4. Professional formatting with source attribution

🎯 Only Captain and Commanders can manage broadcast settings.
    """

    await msg.reply_text(help_text)


# Channel post handlers
async def handle_channel_post(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle new channel posts for broadcasting"""
    await BroadcastService.handle_channel_post(update, context)


async def handle_channel_edited_post(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle edited channel posts for broadcasting"""
    await BroadcastService.handle_channel_edited_post(update, context)


def register(app) -> None:
    """Register ACN broadcast commands and handlers"""
    # Commands
    app.add_handler(CommandHandler("addbroadcast", add_broadcast_channel_cmd))
    app.add_handler(CommandHandler("removebroadcast", remove_broadcast_channel_cmd))
    app.add_handler(CommandHandler("addmaingroup", add_main_group_cmd))
    app.add_handler(CommandHandler("broadcastchannels", list_broadcast_channels))
    app.add_handler(CommandHandler("broadcaststatus", broadcast_status))
    app.add_handler(CommandHandler("testbroadcast", test_broadcast))
    app.add_handler(CommandHandler("broadcasthelp", broadcast_help))

    # Channel post handlers (for automatic broadcasting)
    app.add_handler(
        MessageHandler(tg_filters.UpdateType.CHANNEL_POST, handle_channel_post),
        group=2,  # Priority for channel posts (after message_tracker)
    )
    app.add_handler(
        MessageHandler(
            tg_filters.UpdateType.EDITED_CHANNEL_POST, handle_channel_edited_post
        ),
        group=2,  # Priority for edited channel posts (after message_tracker)
    )

from __future__ import annotations

import asyncio
import time

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Message, Update
from telegram.ext import ContextTypes

from database import async_session_factory
from gateway.websocket import emit_system_event
from models.loyalty import ACNWhitelist
from services.event_service import emit_group_update

logger = structlog.get_logger(__name__)


class BroadcastService:
    """Professional ACN channel broadcast service"""

    @staticmethod
    async def is_acn_channel(channel_id: int) -> bool:
        """Check if channel is whitelisted for ACN broadcasts"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.entity_id == channel_id,
                    ACNWhitelist.whitelist_type == "channel",
                    ACNWhitelist.is_active,
                )
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_main_acn_groups() -> list[int]:
        """Get all main ACN groups for broadcasting"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist.entity_id).where(
                    ACNWhitelist.whitelist_type == "group",
                    ACNWhitelist.is_active,
                    ACNWhitelist.role.in_(["main_group", "broadcast_group"]),
                )
            )
            return [row[0] for row in result.fetchall()]

    @staticmethod
    async def add_broadcast_channel(
        session: AsyncSession,
        channel_id: int,
        channel_name: str,
        channel_type: str = "announcement",
        added_by: int | None = None,
    ) -> ACNWhitelist:
        """Add channel to ACN broadcast whitelist"""
        whitelist = ACNWhitelist(
            entity_id=channel_id,
            entity_name=channel_name,
            whitelist_type="channel",
            role=channel_type,
            added_by=added_by,
            notes="ACN broadcast channel",
        )
        session.add(whitelist)
        await session.flush()
        return whitelist

    @staticmethod
    async def remove_broadcast_channel(session: AsyncSession, channel_id: int) -> bool:
        """Remove channel from ACN broadcast whitelist"""
        result = await session.execute(
            select(ACNWhitelist).where(
                ACNWhitelist.entity_id == channel_id,
                ACNWhitelist.whitelist_type == "channel",
            )
        )
        whitelist_entry = result.scalar_one_or_none()
        if whitelist_entry:
            await session.delete(whitelist_entry)
            return True
        return False

    @staticmethod
    async def format_broadcast_message(
        message: Message, channel_name: str, channel_type: str
    ) -> str:
        """Format professional broadcast message"""
        # Get message content
        content = message.text or message.caption or ""

        # Determine broadcast type
        if channel_type == "announcement":
            emoji = "📢"
            prefix = "**OFFICIAL ANNOUNCEMENT**"
        elif channel_type == "update":
            emoji = "🔄"
            prefix = "**NETWORK UPDATE**"
        elif channel_type == "news":
            emoji = "📰"
            prefix = "**ACN NEWS**"
        elif channel_type == "event":
            emoji = "🎉"
            prefix = "**ACN EVENT**"
        else:
            emoji = "📋"
            prefix = "**ACN BROADCAST**"

        # Format timestamp
        timestamp = time.strftime(
            "%Y-%m-%d %H:%M UTC", time.gmtime(message.date.timestamp())
        )

        # Build broadcast message
        broadcast = f"{emoji} {prefix}\n\n"
        broadcast += f"📺 **Source:** {channel_name}\n"
        broadcast += f"🕐 **Posted:** {timestamp}\n\n"

        # Add content with proper formatting
        if content:
            # Limit content length to prevent very long messages
            if len(content) > 2000:
                content = content[:2000] + "...\n\n*(Message truncated)*"
            broadcast += f"📝 **Content:**\n{content}\n"

        # Add media information
        if message.photo:
            broadcast += "🖼️ **Media:** Photo\n"
        elif message.video:
            broadcast += "🎥 **Media:** Video\n"
        elif message.document:
            broadcast += "📎 **Media:** Document\n"
        elif message.audio:
            broadcast += "🎵 **Media:** Audio\n"
        elif message.voice:
            broadcast += "🎤 **Media:** Voice Note\n"

        # Add footer
        broadcast += "\n—\n🌸 *Broadcasted by Nico Robin Bot*\n"
        broadcast += "⚓ *Anime Crew Network*"

        return broadcast

    @staticmethod
    async def broadcast_to_main_groups(
        context: ContextTypes.DEFAULT_TYPE,
        message: Message,
        channel_name: str,
        channel_type: str,
    ) -> dict:
        """Broadcast message to all main ACN groups"""
        main_groups = await BroadcastService.get_main_acn_groups()

        if not main_groups:
            return {"success": False, "error": "No main ACN groups found"}

        # Format broadcast message
        broadcast_text = await BroadcastService.format_broadcast_message(
            message, channel_name, channel_type
        )

        # Broadcast statistics
        stats = {
            "total_groups": len(main_groups),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

        # Send to each main group
        for group_id in main_groups:
            try:
                # Send text broadcast
                await context.bot.send_message(
                    chat_id=group_id,
                    text=broadcast_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )

                # If original message has media, forward it
                if message.photo or message.video or message.document:
                    await context.bot.forward_message(
                        chat_id=group_id,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id,
                    )

                stats["successful"] += 1

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"Group {group_id}: {str(e)}")

        return stats

    @staticmethod
    async def handle_channel_post(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Handle new channel post for broadcasting"""
        message = update.channel_post
        if not message or not message.chat:
            return False

        channel_id = message.chat.id
        channel_name = message.chat.title or f"Channel {channel_id}"

        # Check if this is an ACN channel
        if not await BroadcastService.is_acn_channel(channel_id):
            return False

        # Get channel type from whitelist
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.entity_id == channel_id,
                    ACNWhitelist.whitelist_type == "channel",
                    ACNWhitelist.is_active,
                )
            )
            whitelist_entry = result.scalar_one_or_none()

            if not whitelist_entry:
                return False

            channel_type = whitelist_entry.role

        # Broadcast to main groups
        try:
            # Extract content for event logging
            content = message.text or message.caption or ""

            stats = await BroadcastService.broadcast_to_main_groups(
                context, message, channel_name, channel_type
            )

            # Log broadcast result
            if stats["successful"] > 0:
                print(
                    f"✅ Broadcast successful: {stats['successful']}/{stats['total_groups']} groups"
                )

                # Emit real-time events
                try:
                    await emit_group_update(
                        update_type="channel_broadcast",
                        group_id=channel_id,
                        actor_id=None,
                        extra_data={
                            "channel_name": channel_name,
                            "channel_type": channel_type,
                            "broadcast_stats": stats,
                        },
                    )

                    # Emit system-wide broadcast notification
                    await emit_system_event(
                        "channel_broadcast",
                        {
                            "channel_name": channel_name,
                            "channel_type": channel_type,
                            "message_preview": (
                                content[:100] + "..." if len(content) > 100 else content
                            ),
                            "broadcast_stats": stats,
                            "timestamp": time.time(),
                        },
                    )
                except Exception as e:
                    print(f"Failed to emit broadcast success events: {e}")
            else:
                print(f"❌ Broadcast failed: {stats.get('error', 'Unknown error')}")

                # Emit system error notification
                try:
                    await emit_system_event(
                        "broadcast_error",
                        {
                            "channel_name": channel_name,
                            "channel_type": channel_type,
                            "error": stats.get("error", "Unknown error"),
                            "timestamp": time.time(),
                        },
                    )
                except Exception as e:
                    print(f"Failed to emit broadcast error event: {e}")

            return True

        except Exception as e:
            print(f"❌ Broadcast error: {e}")
            return False

    @staticmethod
    async def handle_channel_edited_post(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Handle edited channel post for broadcasting updates"""
        message = update.edited_channel_post
        if not message or not message.chat:
            return False

        # For edited posts, we can add a special "UPDATE" prefix
        channel_id = message.chat.id
        channel_name = message.chat.title or f"Channel {channel_id}"

        if not await BroadcastService.is_acn_channel(channel_id):
            return False

        # Get channel type
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.entity_id == channel_id,
                    ACNWhitelist.whitelist_type == "channel",
                    ACNWhitelist.is_active,
                )
            )
            whitelist_entry = result.scalar_one_or_none()

            if not whitelist_entry:
                return False

        # Create update message
        content = message.text or message.caption or ""
        timestamp = time.strftime(
            "%Y-%m-%d %H:%M UTC", time.gmtime(message.date.timestamp())
        )

        update_text = "🔄 **CONTENT UPDATE**\n\n"
        update_text += f"📺 **Source:** {channel_name}\n"
        update_text += f"🕐 **Updated:** {timestamp}\n\n"
        update_text += f"📝 **Updated Content:**\n{content[:1000]}...\n\n"
        update_text += "—\n🌸 *Updated broadcast by Nico Robin Bot*\n"
        update_text += "⚓ *Anime Crew Network*"

        # Broadcast update
        main_groups = await BroadcastService.get_main_acn_groups()
        successful = 0

        for group_id in main_groups:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=update_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                successful += 1
            except Exception:
                pass

        return successful > 0


# Broadcast management functions
async def add_broadcast_channel(
    channel_id: int,
    channel_name: str,
    channel_type: str = "announcement",
    added_by: int | None = None,
) -> bool:
    """Add channel to broadcast whitelist"""
    try:
        async with async_session_factory() as session:
            async with session.begin():
                await BroadcastService.add_broadcast_channel(
                    session, channel_id, channel_name, channel_type, added_by
                )
        return True
    except Exception:
        return False


async def remove_broadcast_channel(channel_id: int) -> bool:
    """Remove channel from broadcast whitelist"""
    try:
        async with async_session_factory() as session:
            async with session.begin():
                return await BroadcastService.remove_broadcast_channel(
                    session, channel_id
                )
    except Exception:
        return False


async def get_broadcast_channels() -> list[dict]:
    """Get all broadcast channels"""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ACNWhitelist).where(
                    ACNWhitelist.whitelist_type == "channel",
                    ACNWhitelist.is_active,
                )
            )

            channels = []
            for entry in result.scalars().all():
                channels.append(
                    {
                        "channel_id": entry.entity_id,
                        "channel_name": entry.entity_name,
                        "channel_type": entry.role,
                        "added_at": (
                            entry.created_at.isoformat() if entry.created_at else None
                        ),
                    }
                )

            return channels
    except Exception:
        return []


async def add_main_group(
    group_id: int, group_name: str, added_by: int | None = None
) -> bool:
    """Add group as main ACN group for broadcasts"""
    try:
        async with async_session_factory() as session:
            async with session.begin():
                # Check if already exists
                result = await session.execute(
                    select(ACNWhitelist).where(
                        ACNWhitelist.entity_id == group_id,
                        ACNWhitelist.whitelist_type == "group",
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update role to main_group
                    existing.role = "main_group"
                else:
                    # Add new entry
                    whitelist = ACNWhitelist(
                        entity_id=group_id,
                        entity_name=group_name,
                        whitelist_type="group",
                        role="main_group",
                        added_by=added_by,
                        notes="Main ACN group for broadcasts",
                    )
                    session.add(whitelist)

        return True
    except Exception:
        return False

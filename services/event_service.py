from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory
from gateway.websocket import emit_realtime_event
from models.event import (
    EventAuditLog,
    EventSubscription,
    RealtimeEvent,
    WebSocketConnection,
)

logger = logging.getLogger(__name__)


class EventService:
    """Service for managing real-time events and WebSocket broadcasting"""

    @staticmethod
    async def create_event(
        session: AsyncSession,
        event_type: str,
        event_data: dict[str, Any],
        group_id: int | None = None,
        user_id: int | None = None,
        target_user_id: int | None = None,
        broadcast_immediately: bool = True,
    ) -> RealtimeEvent:
        """Create a new real-time event"""
        event = RealtimeEvent(
            event_type=event_type,
            event_data=json.dumps(event_data),
            group_id=group_id,
            user_id=user_id,
            target_user_id=target_user_id,
            processed=False,
        )

        session.add(event)
        await session.flush()

        if broadcast_immediately:
            asyncio.create_task(EventService._broadcast_event(event.id))

        return event

    @staticmethod
    async def _broadcast_event(event_id: int):
        """Broadcast event to connected clients"""
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    # Get event with relationships
                    result = await session.execute(
                        select(RealtimeEvent).where(RealtimeEvent.event_id == event_id)
                    )
                    event = result.scalar_one_or_none()

                    if not event or event.processed:
                        return

                    # Parse event data
                    try:
                        event_data = json.loads(event.event_data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in event {event_id}")
                        return

                    # Determine target and broadcast
                    start_time = asyncio.get_event_loop().time()
                    recipients_count = 0

                    if event.group_id:
                        # Broadcast to group room
                        await emit_realtime_event(
                            event.event_type, event_data, "group", str(event.group_id)
                        )
                        recipients_count = await EventService._count_group_connections(
                            session, event.group_id
                        )

                    if event.user_id:
                        # Send to specific user
                        await emit_realtime_event(
                            event.event_type, event_data, "user", str(event.user_id)
                        )

                    if event.target_user_id and event.target_user_id != event.user_id:
                        # Send to target user
                        await emit_realtime_event(
                            event.event_type,
                            event_data,
                            "user",
                            str(event.target_user_id),
                        )

                    # Mark as processed
                    event.processed = True
                    event.broadcast_at = datetime.now(UTC)

                    # Create audit log
                    processing_time = int(
                        (asyncio.get_event_loop().time() - start_time) * 1000
                    )
                    audit_log = EventAuditLog(
                        event_id=event_id,
                        action="broadcast",
                        status="success",
                        recipients_count=recipients_count,
                        processing_time_ms=processing_time,
                    )
                    session.add(audit_log)

                    logger.info(
                        f"Broadcasted event {event_id} ({event.event_type}) to {recipients_count} recipients"
                    )

        except Exception as e:
            logger.error(f"Failed to broadcast event {event_id}: {e}")

            # Create error audit log
            try:
                async with async_session_factory() as session:
                    async with session.begin():
                        audit_log = EventAuditLog(
                            event_id=event_id,
                            action="broadcast",
                            status="error",
                            error_message=str(e),
                            recipients_count=0,
                            processing_time_ms=0,
                        )
                        session.add(audit_log)
            except Exception:
                pass  # Avoid infinite error loops

    @staticmethod
    async def _count_group_connections(session: AsyncSession, group_id: int) -> int:
        """Count active WebSocket connections for a group"""
        result = await session.execute(
            select(WebSocketConnection).where(
                WebSocketConnection.group_id == group_id,
                WebSocketConnection.is_active,
            )
        )
        return len(result.scalars().all())

    @staticmethod
    async def register_websocket_connection(
        session: AsyncSession,
        connection_id: str,
        user_id: int | None = None,
        group_id: int | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> WebSocketConnection:
        """Register a new WebSocket connection"""
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            group_id=group_id,
            connected_at=datetime.now(UTC),
            last_ping=datetime.now(UTC),
            is_active=True,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        session.add(connection)
        await session.flush()

        logger.info(
            f"Registered WebSocket connection {connection_id} for user {user_id}"
        )
        return connection

    @staticmethod
    async def unregister_websocket_connection(
        session: AsyncSession, connection_id: str
    ):
        """Unregister a WebSocket connection"""
        await session.execute(
            update(WebSocketConnection)
            .where(WebSocketConnection.connection_id == connection_id)
            .values(is_active=False)
        )

        logger.info(f"Unregistered WebSocket connection {connection_id}")

    @staticmethod
    async def update_connection_ping(session: AsyncSession, connection_id: str):
        """Update last ping time for connection"""
        await session.execute(
            update(WebSocketConnection)
            .where(WebSocketConnection.connection_id == connection_id)
            .values(last_ping=datetime.now(UTC))
        )

    @staticmethod
    async def cleanup_inactive_connections(
        session: AsyncSession, timeout_minutes: int = 5
    ):
        """Clean up inactive connections"""
        from datetime import timedelta

        cutoff_datetime = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

        await session.execute(
            update(WebSocketConnection)
            .where(WebSocketConnection.last_ping < cutoff_datetime)
            .values(is_active=False)
        )

        logger.info(
            f"Cleaned up inactive connections older than {timeout_minutes} minutes"
        )

    @staticmethod
    async def subscribe_to_events(
        session: AsyncSession,
        user_id: int,
        event_type: str,
        group_id: int | None = None,
    ) -> EventSubscription:
        """Subscribe user to specific event type"""
        subscription = EventSubscription(
            user_id=user_id,
            event_type=event_type,
            group_id=group_id,
            is_active=True,
        )

        session.add(subscription)
        await session.flush()

        logger.info(f"User {user_id} subscribed to {event_type} events")
        return subscription

    @staticmethod
    async def unsubscribe_from_events(
        session: AsyncSession,
        user_id: int,
        event_type: str,
        group_id: int | None = None,
    ):
        """Unsubscribe user from specific event type"""
        await session.execute(
            delete(EventSubscription).where(
                EventSubscription.user_id == user_id,
                EventSubscription.event_type == event_type,
                (
                    EventSubscription.group_id == group_id
                    if group_id is not None
                    else EventSubscription.group_id.is_(None)
                ),
            )
        )

        logger.info(f"User {user_id} unsubscribed from {event_type} events")

    @staticmethod
    async def get_user_subscriptions(
        session: AsyncSession,
        user_id: int,
        group_id: int | None = None,
    ) -> list[EventSubscription]:
        """Get user's event subscriptions"""
        query = select(EventSubscription).where(
            EventSubscription.user_id == user_id, EventSubscription.is_active
        )

        if group_id is not None:
            query = query.where(EventSubscription.group_id == group_id)
        else:
            query = query.where(EventSubscription.group_id.is_(None))

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_connection_stats(session: AsyncSession) -> dict[str, Any]:
        """Get WebSocket connection statistics"""
        # Total active connections
        total_result = await session.execute(
            select(WebSocketConnection).where(WebSocketConnection.is_active)
        )
        total_connections = len(total_result.scalars().all())

        # Connections by group
        group_result = await session.execute(
            select(WebSocketConnection.group_id, WebSocketConnection.user_id)
            .where(WebSocketConnection.is_active)
            .group_by(WebSocketConnection.group_id, WebSocketConnection.user_id)
        )
        group_connections = {}
        for group_id, user_id in group_result:
            if group_id not in group_connections:
                group_connections[group_id] = set()
            group_connections[group_id].add(user_id)

        # Recent events
        from datetime import timedelta

        cutoff_datetime = datetime.now(UTC) - timedelta(hours=1)
        recent_result = await session.execute(
            select(RealtimeEvent)
            .where(RealtimeEvent.created_at >= cutoff_datetime)  # Last hour
            .order_by(RealtimeEvent.created_at.desc())
            .limit(100)
        )
        recent_events = list(recent_result.scalars().all())

        return {
            "total_connections": total_connections,
            "group_connections": {
                str(gid): len(users)
                for gid, users in group_connections.items()
                if gid is not None
            },
            "recent_events_count": len(recent_events),
            "event_types": list(set(event.event_type for event in recent_events)),
        }


# Convenience functions for common event types
async def emit_user_action(
    action: str,
    user_id: int,
    group_id: int,
    actor_id: int | None = None,
    reason: str | None = None,
    extra_data: dict[str, Any] | None = None,
):
    """Emit user action event"""
    event_data = {
        "action": action,
        "user_id": user_id,
        "group_id": group_id,
        "actor_id": actor_id,
        "reason": reason,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if extra_data:
        event_data.update(extra_data)

    async with async_session_factory() as session:
        await EventService.create_event(
            session=session,
            event_type=f"user_{action}",
            event_data=event_data,
            group_id=group_id,
            user_id=actor_id,
            target_user_id=user_id,
        )


async def emit_moderation_action(
    action: str,
    group_id: int,
    target_user_id: int | None = None,
    actor_id: int | None = None,
    reason: str | None = None,
    extra_data: dict[str, Any] | None = None,
):
    """Emit moderation action event"""
    event_data = {
        "action": action,
        "group_id": group_id,
        "target_user_id": target_user_id,
        "actor_id": actor_id,
        "reason": reason,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if extra_data:
        event_data.update(extra_data)

    async with async_session_factory() as session:
        await EventService.create_event(
            session=session,
            event_type=f"moderation_{action}",
            event_data=event_data,
            group_id=group_id,
            user_id=actor_id,
            target_user_id=target_user_id,
        )


async def emit_group_update(
    update_type: str,
    group_id: int,
    actor_id: int | None = None,
    old_value: Any | None = None,
    new_value: Any | None = None,
    extra_data: dict[str, Any] | None = None,
):
    """Emit group update event"""
    event_data = {
        "update_type": update_type,
        "group_id": group_id,
        "actor_id": actor_id,
        "old_value": old_value,
        "new_value": new_value,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if extra_data:
        event_data.update(extra_data)

    async with async_session_factory() as session:
        await EventService.create_event(
            session=session,
            event_type=f"group_{update_type}",
            event_data=event_data,
            group_id=group_id,
            user_id=actor_id,
        )

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import socketio
from telegram.ext import Application

from config import settings

logger = logging.getLogger(__name__)


class BotWebSocketClient:
    """WebSocket client for bot real-time event handling"""

    def __init__(self, bot_app: Application):
        self.bot = bot_app
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=1,
            reconnection_delay_max=5,
        )
        self.connected = False
        self.reconnect_attempts = 0
        self.event_handlers: dict[str, Callable] = {}

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register Socket.IO client event handlers"""
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("connect_error", self._on_connect_error)
        self.sio.on("realtime_event", self._on_realtime_event)
        self.sio.on("authenticated", self._on_authenticated)
        self.sio.on("auth_error", self._on_auth_error)

    async def connect(self, bot_user_id: int):
        """Connect to WebSocket server"""
        if not settings.websocket_enabled:
            logger.info("WebSocket is disabled, skipping connection")
            return

        try:
            # Connect to WebSocket server (Socket.IO is mounted on the same HTTP port)
            await self.sio.connect(
                f"http://127.0.0.1:{settings.port}",
                auth={
                    "bot_id": bot_user_id,
                    "token": "bot_token",
                },  # TODO: Use proper auth
            )

            # Authenticate as bot
            await self.sio.emit(
                "authenticate",
                {
                    "user_id": bot_user_id,
                    "token": "bot_token",  # TODO: Use proper JWT token
                },
            )

            # Join admin room for system events
            await self.sio.emit("join_room", {"room_id": "admins"})

            logger.info(f"Bot WebSocket client connected for user {bot_user_id}")

        except Exception as e:
            logger.error(f"Failed to connect WebSocket client: {e}")
            self.reconnect_attempts += 1

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.connected:
            await self.sio.disconnect()
            self.connected = False
            logger.info("Bot WebSocket client disconnected")

    async def _on_connect(self):
        """Handle connection event"""
        self.connected = True
        self.reconnect_attempts = 0
        logger.info("Bot WebSocket client connected to server")

    async def _on_disconnect(self):
        """Handle disconnection event"""
        self.connected = False
        logger.warning("Bot WebSocket client disconnected from server")

    async def _on_connect_error(self, data):
        """Handle connection error"""
        logger.error(f"WebSocket connection error: {data}")
        self.reconnect_attempts += 1

        if self.reconnect_attempts < 10:
            # Try to reconnect after delay
            await asyncio.sleep(min(self.reconnect_attempts * 2, 30))
            try:
                await self.connect(self.bot.bot.id)
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")

    async def _on_authenticated(self, data):
        """Handle authentication success"""
        logger.info(f"Bot WebSocket client authenticated: {data}")

    async def _on_auth_error(self, data):
        """Handle authentication error"""
        logger.error(f"Bot WebSocket authentication failed: {data}")

    async def _on_realtime_event(self, data):
        """Handle real-time event from server"""
        try:
            event_type = data.get("type")
            event_data = data.get("data", {})

            logger.info(f"Received real-time event: {event_type}")

            # Call registered event handler
            if event_type in self.event_handlers:
                handler = self.event_handlers[event_type]
                await handler(event_data)
            else:
                # Default event handling
                await self._handle_default_event(event_type, event_data)

        except Exception as e:
            logger.error(f"Error handling real-time event: {e}")

    async def _handle_default_event(self, event_type: str, event_data: dict[str, Any]):
        """Default event handling logic"""
        # Handle different event types
        if event_type.startswith("user_"):
            await self._handle_user_event(event_type, event_data)
        elif event_type.startswith("moderation_"):
            await self._handle_moderation_event(event_type, event_data)
        elif event_type.startswith("group_"):
            await self._handle_group_event(event_type, event_data)
        elif event_type.startswith("system_"):
            await self._handle_system_event(event_type, event_data)

    async def _handle_user_event(self, event_type: str, event_data: dict[str, Any]):
        """Handle user-related events"""
        group_id = event_data.get("group_id")
        user_id = event_data.get("user_id")
        action = event_data.get("action")

        if not group_id or not user_id or not action:
            return

        # Log user action for monitoring
        logger.info(f"User event in group {group_id}: {action} for user {user_id}")

        # Could trigger additional bot actions here
        # For example: send notifications, update statistics, etc.

    async def _handle_moderation_event(
        self, event_type: str, event_data: dict[str, Any]
    ):
        """Handle moderation-related events"""
        group_id = event_data.get("group_id")
        action = event_data.get("action")
        target_user_id = event_data.get("target_user_id")

        if not group_id or not action:
            return

        logger.info(f"Moderation event in group {group_id}: {action}")

        # Could trigger admin notifications, logging, etc.
        if target_user_id:
            logger.info(
                f"Moderation action {action} on user {target_user_id} in group {group_id}"
            )

    async def _handle_group_event(self, event_type: str, event_data: dict[str, Any]):
        """Handle group-related events"""
        group_id = event_data.get("group_id")
        update_type = event_data.get("update_type")

        if not group_id or not update_type:
            return

        logger.info(f"Group event: {update_type} for group {group_id}")

        # Could trigger cache updates, synchronization, etc.

    async def _handle_system_event(self, event_type: str, event_data: dict[str, Any]):
        """Handle system-related events"""
        logger.info(f"System event: {event_type}")

        # Handle system-wide events
        if event_type == "bot_status":
            status = event_data.get("status")
            logger.info(f"Bot status update: {status}")
        elif event_type == "performance_alert":
            alert = event_data.get("alert")
            logger.warning(f"Performance alert: {alert}")
        elif event_type == "maintenance_mode":
            enabled = event_data.get("enabled")
            logger.info(f"Maintenance mode: {'enabled' if enabled else 'disabled'}")

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register custom event handler"""
        self.event_handlers[event_type] = handler
        logger.info(f"Registered event handler for {event_type}")

    def unregister_event_handler(self, event_type: str):
        """Unregister event handler"""
        if event_type in self.event_handlers:
            del self.event_handlers[event_type]
            logger.info(f"Unregistered event handler for {event_type}")

    async def join_group_room(self, group_id: int):
        """Join a group-specific room"""
        if self.connected:
            await self.sio.emit("join_room", {"room_id": f"group_{group_id}"})
            logger.info(f"Joined group room: {group_id}")

    async def leave_group_room(self, group_id: int):
        """Leave a group-specific room"""
        if self.connected:
            await self.sio.emit("leave_room", {"room_id": f"group_{group_id}"})
            logger.info(f"Left group room: {group_id}")

    async def send_event(self, event_type: str, data: dict[str, Any]):
        """Send event to WebSocket server"""
        if self.connected:
            await self.sio.emit(
                "bot_event",
                {
                    "type": event_type,
                    "data": data,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            )
            logger.info(f"Sent bot event: {event_type}")

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected


# Global WebSocket client instance
bot_websocket_client: BotWebSocketClient | None = None


async def initialize_websocket_client(bot_app: Application):
    """Initialize the WebSocket client"""
    global bot_websocket_client

    if settings.websocket_enabled:
        bot_websocket_client = BotWebSocketClient(bot_app)

        # Get bot user ID
        bot_user = await bot_app.bot.get_me()
        await bot_websocket_client.connect(bot_user.id)

        logger.info("WebSocket client initialized")
    else:
        logger.info("WebSocket client disabled")


async def shutdown_websocket_client():
    """Shutdown the WebSocket client"""
    global bot_websocket_client

    if bot_websocket_client:
        await bot_websocket_client.disconnect()
        bot_websocket_client = None
        logger.info("WebSocket client shutdown")


def get_websocket_client() -> BotWebSocketClient | None:
    """Get the global WebSocket client instance"""
    return bot_websocket_client


# Decorator for registering event handlers
def websocket_event_handler(event_type: str):
    """Decorator to register WebSocket event handlers"""

    def decorator(func):
        async def wrapper(event_data):
            try:
                await func(event_data)
            except Exception as e:
                logger.error(f"Error in WebSocket event handler for {event_type}: {e}")

        # Register with global client if available
        client = get_websocket_client()
        if client:
            client.register_event_handler(event_type, wrapper)

        return wrapper

    return decorator

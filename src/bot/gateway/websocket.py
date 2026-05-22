"""WebSocket gateway — hardened with HMAC auth, CORS lockdown, and connection limits."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any

import socketio

from src.bot.config import settings

logger = logging.getLogger(__name__)


def _verify_hmac_token(user_id: str, timestamp: str, token: str) -> bool:
    """Verify HMAC-SHA256 token: HMAC(user_id:timestamp, secret)."""
    secret = settings.webhook_secret or settings.bot_token
    if not secret:
        return False
    try:
        ts = float(timestamp)
        if abs(time.time() - ts) > 300:
            return False  # 5 min window
    except (ValueError, TypeError):
        return False
    payload = f"{user_id}:{timestamp}".encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)


class WebSocketManager:
    """Hardened WebSocket manager with authentication and abuse protection."""

    def __init__(self):
        cors = settings.websocket_cors_origin
        if cors == "*" and settings.environment == "production":
            cors = []
            logger.warning("CORS wildcard blocked in production")
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=cors if cors != "*" else "*",
            ping_interval=settings.websocket_ping_interval,
            ping_timeout=settings.websocket_ping_timeout,
            max_http_buffer_size=1_000_000,
        )
        self.active_connections: dict[str, set[str]] = {}
        self.user_sessions: dict[str, str] = {}
        self.session_rooms: dict[str, set[str]] = {}
        self._authenticated: set[str] = set()
        self._connect_times: dict[str, float] = {}
        self._register_handlers()

    def _register_handlers(self):
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("join_room", self._on_join_room)
        self.sio.on("leave_room", self._on_leave_room)
        self.sio.on("authenticate", self._on_authenticate)
        self.sio.on("bot_event", self._on_bot_event)

    async def _on_connect(
        self, sid: str, environ: dict[str, Any], auth: dict[str, Any] | None = None
    ):
        logger.info(f"WS connect: {sid}")
        self._connect_times[sid] = time.time()

        # Immediate authentication if auth data is provided (Socket.IO 5.x+)
        if auth:
            user_id = auth.get("user_id") or auth.get("bot_id")
            token = auth.get("token")
            timestamp = auth.get("timestamp")
            if user_id and token and timestamp:
                if _verify_hmac_token(str(user_id), str(timestamp), str(token)):
                    self._authenticated.add(sid)
                    self.user_sessions[sid] = str(user_id)
                    logger.info(f"WS auto-authenticated: {sid}, user={user_id}")
                else:
                    logger.warning(f"WS auto-auth failed: {sid}, user={user_id}")

        await self.sio.emit("connected", {"status": "ok", "sid": sid}, room=sid)
        # Auto-disconnect unauthenticated clients after 10s
        asyncio.get_event_loop().call_later(
            10.0,
            lambda: asyncio.ensure_future(self._auth_timeout(sid)),
        )

    async def _auth_timeout(self, sid: str):
        if sid not in self._authenticated and sid in self._connect_times:
            logger.warning(f"WS auth timeout, disconnecting: {sid}")
            try:
                await self.sio.disconnect(sid)
            except Exception:
                pass

    async def _on_disconnect(self, sid: str):
        logger.info(f"WS disconnect: {sid}")
        self._authenticated.discard(sid)
        self._connect_times.pop(sid, None)
        self.user_sessions.pop(sid, None)
        rooms = self.session_rooms.pop(sid, set())
        for room_id in rooms:
            if room_id in self.active_connections:
                self.active_connections[room_id].discard(sid)
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]

    async def _on_authenticate(self, sid: str, data: dict[str, Any]):
        user_id = data.get("user_id")
        token = data.get("token")
        timestamp = data.get("timestamp")
        if not user_id or not token or not timestamp:
            await self.sio.emit(
                "auth_error", {"error": "Missing credentials"}, room=sid
            )
            return
        if not _verify_hmac_token(str(user_id), str(timestamp), str(token)):
            logger.warning(f"WS auth failed: {sid}, user={user_id}")
            await self.sio.emit("auth_error", {"error": "Invalid token"}, room=sid)
            try:
                from src.bot.services.security_logger import SecurityLogger

                await SecurityLogger.log_event(
                    "ws_auth_failed",
                    user_id=(
                        int(user_id) if str(user_id).lstrip("-").isdigit() else None
                    ),
                    severity="MEDIUM",
                )
            except Exception:
                pass
            await self.sio.disconnect(sid)
            return
        self._authenticated.add(sid)
        self.user_sessions[sid] = str(user_id)
        await self.sio.emit("authenticated", {"user_id": user_id}, room=sid)

    async def _on_join_room(self, sid: str, data: dict[str, Any]):
        if sid not in self._authenticated:
            await self.sio.emit("error", {"error": "Not authenticated"}, room=sid)
            return
        room_id = data.get("room_id")
        if not room_id:
            return
        # Admin rooms restricted to sudo/captain/commander
        if room_id == "admins":
            uid = self.user_sessions.get(sid)
            if uid:
                uid_int = int(uid) if uid.lstrip("-").isdigit() else 0
                # Check if it's the bot itself (extract bot_id from token)
                bot_id_str = (
                    settings.bot_token.split(":")[0]
                    if ":" in settings.bot_token
                    else ""
                )
                bot_id = int(bot_id_str) if bot_id_str.isdigit() else 0

                if (
                    uid_int not in settings.sudo_users
                    and uid_int != settings.captain_id
                    and uid_int not in settings.commander_ids
                    and uid_int != bot_id  # Allow the bot itself
                ):
                    await self.sio.emit(
                        "error", {"error": "Admin room restricted"}, room=sid
                    )
                    return
        await self.sio.enter_room(sid, room_id)
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(sid)
        if sid not in self.session_rooms:
            self.session_rooms[sid] = set()
        self.session_rooms[sid].add(room_id)
        await self.sio.emit("joined_room", {"room_id": room_id}, room=sid)

    async def _on_leave_room(self, sid: str, data: dict[str, Any]):
        room_id = data.get("room_id")
        if not room_id:
            return
        await self.sio.leave_room(sid, room_id)
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(sid)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        if sid in self.session_rooms:
            self.session_rooms[sid].discard(room_id)
        await self.sio.emit("left_room", {"room_id": room_id}, room=sid)

    async def _on_bot_event(self, sid: str, data: dict[str, Any]):
        """Handle events emitted by the bot client."""
        if sid not in self._authenticated:
            return
        event_type = data.get("type")
        event_data = data.get("data")
        logger.info(f"Received bot event: {event_type} from {sid}")
        # Forward to other handlers if needed, or broadcast to admins
        if event_type == "bot_status":
            await self.broadcast_to_admins(
                {"event": "bot_status_update", "sid": sid, "data": event_data}
            )

    async def broadcast_to_group(self, group_id: str, event: dict[str, Any]):
        await self.sio.emit("realtime_event", event, room=f"group_{group_id}")

    async def send_to_user(self, user_id: str, event: dict[str, Any]):
        for sid, uid in self.user_sessions.items():
            if uid == user_id:
                await self.sio.emit("realtime_event", event, room=sid)

    async def broadcast_to_admins(self, event: dict[str, Any]):
        await self.sio.emit("realtime_event", event, room="admins")

    async def broadcast_global(self, event: dict[str, Any]):
        await self.sio.emit("realtime_event", event)

    def get_connection_stats(self) -> dict[str, Any]:
        return {
            "total_connections": len(self.user_sessions),
            "authenticated": len(self._authenticated),
            "active_rooms": len(self.active_connections),
            "room_details": {r: len(s) for r, s in self.active_connections.items()},
        }


websocket_manager = WebSocketManager()


def create_socketio_app(other_asgi_app: Any | None = None) -> socketio.ASGIApp:
    return socketio.ASGIApp(websocket_manager.sio, other_asgi_app=other_asgi_app)


async def emit_realtime_event(
    event_type: str,
    data: dict[str, Any],
    target: str = "global",
    target_id: str | None = None,
):
    event = {
        "event": "realtime_update",
        "type": event_type,
        "data": data,
        "timestamp": asyncio.get_event_loop().time(),
        "target": target,
        "target_id": target_id,
    }
    if target == "group" and target_id:
        await websocket_manager.broadcast_to_group(target_id, event)
    elif target == "user" and target_id:
        await websocket_manager.send_to_user(target_id, event)
    elif target == "admins":
        await websocket_manager.broadcast_to_admins(event)
    else:
        await websocket_manager.broadcast_global(event)


USER_EVENTS = {
    "user_joined",
    "user_left",
    "user_banned",
    "user_unbanned",
    "user_warned",
    "user_muted",
    "user_unmuted",
}
MODERATION_EVENTS = {
    "message_deleted",
    "filter_triggered",
    "swear_word_violation",
    "ai_moderation",
    "flood_detected",
}
GROUP_EVENTS = {
    "settings_changed",
    "filter_added",
    "filter_removed",
    "welcome_updated",
    "rules_updated",
}
SYSTEM_EVENTS = {
    "bot_status",
    "performance_alert",
    "error_occurred",
    "maintenance_mode",
    "channel_broadcast",
    "broadcast_error",
}


async def emit_user_event(
    event_type: str, user_id: str, group_id: str, data: dict[str, Any]
):
    if event_type not in USER_EVENTS:
        return
    await emit_realtime_event(event_type, data, "group", group_id)
    await emit_realtime_event(event_type, data, "user", user_id)


async def emit_moderation_event(event_type: str, group_id: str, data: dict[str, Any]):
    if event_type not in MODERATION_EVENTS:
        return
    await emit_realtime_event(event_type, data, "group", group_id)
    await emit_realtime_event(event_type, data, "admins")


async def emit_group_event(event_type: str, group_id: str, data: dict[str, Any]):
    if event_type not in GROUP_EVENTS:
        return
    await emit_realtime_event(event_type, data, "group", group_id)


async def emit_system_event(event_type: str, data: dict[str, Any]):
    if event_type not in SYSTEM_EVENTS:
        return
    await emit_realtime_event(event_type, data, "global")

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.bot.models.group import Group
    from src.bot.models.user import User


class RealtimeEvent(Base, TimestampMixin):
    """Track real-time events for WebSocket broadcasting"""

    __tablename__ = "realtime_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    target_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    broadcast_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    group: Mapped[Group | None] = relationship(foreign_keys=[group_id])
    user: Mapped[User | None] = relationship(foreign_keys=[user_id])
    target_user: Mapped[User | None] = relationship(foreign_keys=[target_user_id])


class WebSocketConnection(Base):
    """Track active WebSocket connections"""

    __tablename__ = "websocket_connections"

    connection_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    connected_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_ping: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    group: Mapped[Group | None] = relationship()
    user: Mapped[User | None] = relationship()


class EventSubscription(Base, TimestampMixin):
    """Track user subscriptions to specific event types"""

    __tablename__ = "event_subscriptions"

    subscription_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[Group | None] = relationship()
    user: Mapped[User] = relationship()


class EventAuditLog(Base):
    """Audit log for all real-time events"""

    __tablename__ = "event_audit_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("realtime_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipients_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    event: Mapped[RealtimeEvent] = relationship()

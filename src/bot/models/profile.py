"""MemberProfile model — tracks per-user per-group activity and profile data."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.user import User


class MemberProfile(TimestampMixin, SoftDeleteMixin, Base):
    """Extended member profile — tracks activity, bio, and engagement metrics."""

    __tablename__ = "member_profiles"
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

    profile_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Activity counters
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stickers_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    photos_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    videos_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    voice_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    commands_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Engagement
    replies_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mentions_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Profile
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Activity patterns
    peak_hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-23
    active_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hourly_activity: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )  # {hour: count}
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Meta
    profile_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()

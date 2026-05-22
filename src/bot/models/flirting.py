from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.user import User


class FlirtingAttempt(Base, TimestampMixin):
    """Track flirting attempts and their outcomes"""

    __tablename__ = "flirting_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", "event_id", "attempt_time"),
    )

    attempt_id: Mapped[int] = mapped_column(
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
    target_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=True)
    successful: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    response_given: Mapped[str] = mapped_column(Text, nullable=True)
    points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_time: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # Unix timestamp
    skill_level: Mapped[str] = mapped_column(
        String(20), default="beginner", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    target_user: Mapped[User | None] = relationship(foreign_keys=[target_user_id])
    group: Mapped[Group] = relationship()


class FlirtingStats(Base, TimestampMixin):
    """User flirting statistics and achievements"""

    __tablename__ = "flirting_stats"
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

    stats_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    total_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_flirts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_flirts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_category: Mapped[str] = mapped_column(
        String(20), default="charming", nullable=False
    )
    highest_skill_used: Mapped[str] = mapped_column(
        String(20), default="beginner", nullable=False
    )
    points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_flirt_time: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flirt_level: Mapped[str] = mapped_column(
        String(20), default="novice", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()


class FlirtingAchievement(Base, TimestampMixin):
    """Flirting achievements and rewards"""

    __tablename__ = "flirting_achievements"

    achievement_id: Mapped[int] = mapped_column(
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
    achievement_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    achievement_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(10), default="🌸", nullable=False)
    points_rewarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unlocked_at: Mapped[int] = mapped_column(Integer, nullable=False)  # Unix timestamp

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()


class FlirtingRelationship(Base, TimestampMixin):
    """Track romantic relationships between users"""

    __tablename__ = "flirting_relationships"
    __table_args__ = (UniqueConstraint("user_id", "partner_id", "group_id"),)

    relationship_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_id: Mapped[int] = mapped_column(
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
    relationship_status: Mapped[str] = mapped_column(
        String(20), default="crush", nullable=False, index=True
    )
    intimacy_level: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0-100
    romance_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    special_moments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[int] = mapped_column(Integer, nullable=False)  # Unix timestamp
    last_interaction: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    partner: Mapped[User] = relationship(foreign_keys=[partner_id])
    group: Mapped[Group] = relationship()


class FlirtingGift(Base, TimestampMixin):
    """Virtual gifts and romantic gestures"""

    __tablename__ = "flirting_gifts"

    gift_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id: Mapped[int] = mapped_column(
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
    gift_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    gift_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    gift_emoji: Mapped[str] = mapped_column(String(10), nullable=False)
    gift_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])
    group: Mapped[Group] = relationship()


class FlirtingPreference(Base, TimestampMixin):
    """User flirting preferences and settings"""

    __tablename__ = "flirting_preferences"
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

    preference_id: Mapped[int] = mapped_column(
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
    preferred_categories: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON string
    blocked_categories: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    max_skill_level: Mapped[str] = mapped_column(
        String(20), default="master", nullable=False
    )
    auto_responses: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    public_flirting: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    receive_gifts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_level: Mapped[str] = mapped_column(
        String(20), default="all", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()

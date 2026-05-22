from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
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


class UserPoints(Base, TimestampMixin):
    """User point balance and tracking"""

    __tablename__ = "user_points"
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

    points_id: Mapped[int] = mapped_column(
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
    current_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_earned: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    last_activity: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp
    selected_apploid: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # Currently selected apploid

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()


class PointTransaction(Base, TimestampMixin):
    """Point transaction history"""

    __tablename__ = "point_transactions"

    transaction_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    transaction_uid: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
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
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # earn, spend, bonus, penalty
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # message, command, reward, etc.
    description: Mapped[str] = mapped_column(Text(), nullable=True)
    transaction_time: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()


class Apploid(Base, TimestampMixin):
    """Custom apploids (emojis/avatars) for point system"""

    __tablename__ = "apploids"

    apploid_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    apploid_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    apploid_emoji: Mapped[str] = mapped_column(String(10), nullable=False)
    apploid_image: Mapped[str] = mapped_column(
        String(255), nullable=True
    )  # URL or file path
    description: Mapped[str] = mapped_column(Text(), nullable=True)
    rarity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # common, rare, epic, legendary
    required_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_owners: Mapped[int] = mapped_column(
        Integer, nullable=True
    )  # For limited apploids
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by])


class UserApploid(Base, TimestampMixin):
    """User-owned apploids"""

    __tablename__ = "user_apploids"
    __table_args__ = (UniqueConstraint("user_id", "group_id", "apploid_id"),)

    user_apploid_id: Mapped[int] = mapped_column(
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
    apploid_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("apploids.apploid_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    purchase_price: Mapped[int] = mapped_column(Integer, nullable=False)
    acquired_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()
    apploid: Mapped[Apploid] = relationship()


class PointReward(Base, TimestampMixin):
    """Rewards that can be redeemed with points"""

    __tablename__ = "point_rewards"

    reward_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    reward_name: Mapped[str] = mapped_column(String(100), nullable=False)
    reward_description: Mapped[str] = mapped_column(Text(), nullable=False)
    reward_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # apploid, role, permission, item
    reward_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_data: Mapped[str] = mapped_column(
        Text(), nullable=True
    )  # JSON string with reward details
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_purchases: Mapped[int] = mapped_column(Integer, nullable=True)
    current_purchases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    required_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expiry_date: Mapped[int] = mapped_column(
        BigInteger, nullable=True
    )  # Unix timestamp

    # Relationships
    redemptions: Mapped[list[PointRedemption]] = relationship(back_populates="reward")


class PointRedemption(Base, TimestampMixin):
    """Record of reward redemptions"""

    __tablename__ = "point_redemptions"

    redemption_id: Mapped[int] = mapped_column(
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
    reward_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("point_rewards.reward_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_data: Mapped[str] = mapped_column(
        Text(), nullable=True
    )  # JSON string with specific reward data
    status: Mapped[str] = mapped_column(
        String(20), default="completed", nullable=False
    )  # pending, completed, failed
    redeemed_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()
    reward: Mapped[PointReward] = relationship(back_populates="redemptions")


class PointStreak(Base, TimestampMixin):
    """User activity streaks for bonus points"""

    __tablename__ = "point_streaks"
    __table_args__ = (UniqueConstraint("user_id", "group_id", "streak_type"),)

    streak_id: Mapped[int] = mapped_column(
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
    streak_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # daily, weekly, monthly
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp
    bonus_multiplier: Mapped[float] = mapped_column(
        Integer, default=1.0, nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()


class PointLeaderboard(Base, TimestampMixin):
    """Leaderboard snapshots for tracking rankings"""

    __tablename__ = "point_leaderboards"

    leaderboard_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leaderboard_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # daily, weekly, monthly, all_time
    top_users: Mapped[str] = mapped_column(
        Text(), nullable=False
    )  # JSON string with top users data
    snapshot_time: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()

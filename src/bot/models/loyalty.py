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

from src.bot.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.user import User


class ACNWhitelist(Base, TimestampMixin):
    """Anime Crew Network whitelist for groups and users"""

    __tablename__ = "acn_whitelist"
    __table_args__ = (UniqueConstraint("whitelist_type", "entity_id"),)

    whitelist_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    whitelist_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'group' or 'user'
    entity_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )  # group_id or user_id
    entity_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # group name or username
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'captain', 'commander', 'member', 'ally'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    group: Mapped[Group | None] = relationship(
        foreign_keys=[entity_id],
        primaryjoin="and_(ACNWhitelist.entity_id==Group.group_id, ACNWhitelist.whitelist_type=='group')",
        overlaps="user",
    )
    user: Mapped[User | None] = relationship(
        foreign_keys=[entity_id],
        primaryjoin="and_(ACNWhitelist.entity_id==User.user_id, ACNWhitelist.whitelist_type=='user')",
        overlaps="group",
    )
    added_by_user: Mapped[User | None] = relationship(foreign_keys=[added_by])


class LoyaltyPoints(Base, TimestampMixin, SoftDeleteMixin):
    """Loyalty points system for ACN members"""

    __tablename__ = "loyalty_points"
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
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[str] = mapped_column(String(50), default="Crew Member", nullable=False)
    total_actions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )  # Unix timestamp

    # Relationships
    user: Mapped[User] = relationship(back_populates="loyalty_points")
    group: Mapped[Group] = relationship()


class LoyaltyReward(Base, TimestampMixin):
    """Redeemable rewards for loyalty points"""

    __tablename__ = "loyalty_rewards"

    reward_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'title', 'role', 'permission', 'custom'
    reward_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    required_role: Mapped[str] = mapped_column(
        String(50), default="member", nullable=False
    )
    usage_limit: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = unlimited
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class LoyaltyRedemption(Base, TimestampMixin):
    """Track reward redemptions"""

    __tablename__ = "loyalty_redemptions"

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
        ForeignKey("loyalty_rewards.reward_id", ondelete="CASCADE"),
        nullable=False,
    )
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, completed, failed
    processed_at: Mapped[int] = mapped_column(
        BigInteger, nullable=True
    )  # Unix timestamp

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()
    reward: Mapped[LoyaltyReward] = relationship()


class ACNActivity(Base, TimestampMixin):
    """Track ACN member activities for loyalty points"""

    __tablename__ = "acn_activities"

    activity_id: Mapped[int] = mapped_column(
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
    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'moderation', 'engagement', 'loyalty'
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extra_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    # Relationships
    user: Mapped[User] = relationship()
    group: Mapped[Group] = relationship()

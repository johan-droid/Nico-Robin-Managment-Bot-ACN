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


class FeatureToggle(Base, TimestampMixin):
    """Feature toggle settings for bot functionality"""

    __tablename__ = "feature_toggles"
    __table_args__ = (UniqueConstraint("group_id", "feature_name"),)

    toggle_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    toggle_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    toggled_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    toggle_level: Mapped[str] = mapped_column(
        String(20), default="group", nullable=False
    )  # global, network, group

    # Relationships
    group: Mapped[Group] = relationship()
    toggled_by_user: Mapped[User | None] = relationship(foreign_keys=[toggled_by])


class GroupFeature(Base):
    """Per-group feature state used by command and event gates."""

    __tablename__ = "group_features"

    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        primary_key=True,
    )
    feature_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[Group] = relationship()


class FeaturePermission(Base, TimestampMixin):
    """Feature permissions by user role"""

    __tablename__ = "feature_permissions"
    __table_args__ = (UniqueConstraint("feature_name", "user_role"),)

    permission_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    feature_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    can_use: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_toggle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string


class FeatureUsage(Base, TimestampMixin):
    """Track feature usage statistics"""

    __tablename__ = "feature_usage"

    usage_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()
    user: Mapped[User] = relationship()


class FeatureLog(Base, TimestampMixin):
    """Log feature toggle changes"""

    __tablename__ = "feature_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # enabled, disabled
    old_value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    toggle_level: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    group: Mapped[Group] = relationship()
    user: Mapped[User | None] = relationship(foreign_keys=[user_id])

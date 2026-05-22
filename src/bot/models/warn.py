from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.models.base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.user import User


class Warn(SoftDeleteMixin, Base):
    __tablename__ = "warns"

    warn_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(
        Text, default="No reason provided", nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_action: Mapped[str | None] = mapped_column(String(32), nullable=True)

    group: Mapped[Group] = relationship(back_populates="warns")
    user: Mapped[User] = relationship(back_populates="warns", foreign_keys=[user_id])
    admin: Mapped[User | None] = relationship(foreign_keys=[admin_id])

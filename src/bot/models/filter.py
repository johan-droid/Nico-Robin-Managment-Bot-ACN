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
    from src.bot.models.group import Group
    from src.bot.models.user import User


class Filter(TimestampMixin, Base):
    __tablename__ = "filters"
    __table_args__ = (UniqueConstraint("group_id", "trigger"),)

    filter_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="reply", nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    regex: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    match_mode: Mapped[str] = mapped_column(String(32), default="contains", nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    group: Mapped[Group] = relationship(back_populates="filters")
    creator: Mapped[User | None] = relationship()

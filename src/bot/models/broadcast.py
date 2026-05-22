from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group


class BroadcastChannelState(Base, TimestampMixin):
    """Track the most recent channel post forwarded for deduplication."""

    __tablename__ = "broadcast_channel_state"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    last_forwarded_message_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    last_forwarded_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class BroadcastDelivery(Base, TimestampMixin):
    """Track each broadcasted copy so edits can be propagated."""

    __tablename__ = "broadcast_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "source_channel_id",
            "source_message_id",
            "destination_group_id",
        ),
    )

    delivery_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    destination_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_message_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )

    group: Mapped[Group] = relationship()
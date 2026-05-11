"""ManagedChannel model - tracks channels for purge/broadcast management."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class ManagedChannel(Base, TimestampMixin):
    """Channels managed by the bot for purge/broadcast operations."""

    __tablename__ = "managed_channels"

    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="purge"
    )  # 'purge' or 'broadcast'
    auto_purge: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_can_post: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

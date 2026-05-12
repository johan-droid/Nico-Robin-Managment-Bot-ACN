from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.audit import ActionLog, JoinLog, MessageLog
    from models.federation import FederationGroup
    from models.filter import Filter
    from models.note import Note
    from models.user import GroupMember
    from models.warn import Warn


class Group(TimestampMixin, Base):
    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    prefix: Mapped[str] = mapped_column(String(8), default="/", nullable=False)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    welcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    farewell_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)

    welcome_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    farewell_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    clean_welcome: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    captcha_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    antispam_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    antiraid_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_mod_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nightmode_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    max_warns: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    warn_action: Mapped[str] = mapped_column(String(32), default="ban", nullable=False)
    mute_time: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    flood_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    flood_action: Mapped[str] = mapped_column(
        String(32), default="mute", nullable=False
    )
    filter_action: Mapped[str] = mapped_column(
        String(32), default="reply", nullable=False
    )
    log_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Swear word settings
    swear_words_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    default_swear_severity: Mapped[str] = mapped_column(
        String(20), default="moderate", nullable=False
    )
    default_swear_punishment: Mapped[str] = mapped_column(
        String(20), default="mute", nullable=False
    )
    default_swear_duration: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )

    locked_media: Mapped[dict[str, bool]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    members: Mapped[list[GroupMember]] = relationship(back_populates="group")
    warns: Mapped[list[Warn]] = relationship(back_populates="group")
    notes: Mapped[list[Note]] = relationship(back_populates="group")
    filters: Mapped[list[Filter]] = relationship(back_populates="group")
    federation_links: Mapped[list[FederationGroup]] = relationship(
        back_populates="group",
    )
    action_logs: Mapped[list[ActionLog]] = relationship(back_populates="group")
    message_logs: Mapped[list[MessageLog]] = relationship(back_populates="group")
    join_logs: Mapped[list[JoinLog]] = relationship(back_populates="group")


class GroupSettingSnapshot(Base):
    """Optional materialized settings cache invalidation marker."""

    __tablename__ = "group_setting_snapshots"

    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        primary_key=True,
    )
    cache_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

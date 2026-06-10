from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bot.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.bot.models.group import Group
    from src.bot.models.user import User


class Federation(TimestampMixin, Base):
    __tablename__ = "federations"

    fed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    groups: Mapped[list[FederationGroup]] = relationship(back_populates="federation")
    admins: Mapped[list[FederationAdmin]] = relationship(back_populates="federation")
    bans: Mapped[list[FederationBan]] = relationship(back_populates="federation")


class FederationGroup(Base):
    __tablename__ = "federation_groups"
    __table_args__ = (UniqueConstraint("fed_id", "group_id"),)

    fed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("federations.fed_id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    federation: Mapped[Federation] = relationship(back_populates="groups")
    group: Mapped[Group] = relationship(back_populates="federation_links")


class FederationAdmin(Base):
    __tablename__ = "federation_admins"
    __table_args__ = (UniqueConstraint("fed_id", "user_id"),)

    fed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("federations.fed_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )

    federation: Mapped[Federation] = relationship(back_populates="admins")
    user: Mapped[User] = relationship()


class FederationBan(Base):
    __tablename__ = "federation_bans"
    __table_args__ = (UniqueConstraint("fed_id", "user_id"),)

    fed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("federations.fed_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        Text, default="No reason provided", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    federation: Mapped[Federation] = relationship(back_populates="bans")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    admin: Mapped[User | None] = relationship(foreign_keys=[admin_id])

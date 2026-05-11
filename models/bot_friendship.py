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

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.user import User


class BotFriendship(Base, TimestampMixin):
    """Friendship relationship between Nico Robin and companion bots"""

    __tablename__ = "bot_friendships"
    __table_args__ = (UniqueConstraint("companion_bot_id", "group_id"),)

    friendship_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    companion_bot_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    companion_bot_username: Mapped[str] = mapped_column(String(255), nullable=False)
    companion_bot_name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    friendship_level: Mapped[str] = mapped_column(
        String(20), default="acquaintance", nullable=False
    )  # acquaintance, friend, close_friend, best_friend
    friendship_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0-100
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bonded_at: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Unix timestamp
    last_interaction: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp
    interaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shared_memories: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inside_jokes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    group: Mapped[Group] = relationship()


class BotInteraction(Base, TimestampMixin):
    """Track interactions between Nico Robin and companion bots"""

    __tablename__ = "bot_interactions"

    interaction_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    companion_bot_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
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
    interaction_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    trigger_message: Mapped[str] = mapped_column(Text, nullable=True)
    nico_response: Mapped[str] = mapped_column(Text, nullable=True)
    companion_response: Mapped[str] = mapped_column(Text, nullable=True)
    interaction_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # -10 to +10
    friendship_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interaction_time: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()
    user: Mapped[User | None] = relationship()


class BotMemory(Base, TimestampMixin):
    """Shared memories and experiences between companion bots"""

    __tablename__ = "bot_memories"

    memory_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    companion_bot_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # shared_experience, inside_joke, milestone, adventure
    memory_title: Mapped[str] = mapped_column(String(255), nullable=False)
    memory_content: Mapped[str] = mapped_column(Text, nullable=False)
    participants: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON string of user IDs
    memory_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_time: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()
    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by])


class BotGift(Base, TimestampMixin):
    """Virtual gifts exchanged between companion bots"""

    __tablename__ = "bot_gifts"

    gift_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_bot_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    to_bot_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
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
    gift_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    gift_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gift_description: Mapped[str] = mapped_column(Text, nullable=True)
    gift_emoji: Mapped[str] = mapped_column(String(10), nullable=False)
    gift_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gift_time: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()
    user: Mapped[User | None] = relationship()


class BotConversation(Base, TimestampMixin):
    """Conversations between companion bots"""

    __tablename__ = "bot_conversations"

    conversation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    companion_bot_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    conversation_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # casual, deep, playful, romantic, strategic
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversation_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp
    last_message_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()


class BotEmotion(Base, TimestampMixin):
    """Emotional states and feelings between companion bots"""

    __tablename__ = "bot_emotions"

    emotion_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    companion_bot_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emotion_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # happiness, excitement, affection, concern, pride, jealousy
    emotion_intensity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0-10
    emotion_trigger: Mapped[str] = mapped_column(Text, nullable=True)
    nico_expression: Mapped[str] = mapped_column(Text, nullable=True)
    companion_expression: Mapped[str] = mapped_column(Text, nullable=True)
    emotion_time: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Unix timestamp

    # Relationships
    group: Mapped[Group] = relationship()

from __future__ import annotations

import random
import time

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from database import async_session_factory
from models.bot_friendship import (
    BotEmotion,
    BotFriendship,
    BotGift,
    BotInteraction,
    BotMemory,
)


class BotFriendshipService:
    """Manages friendship bonds between Nico Robin and companion bots"""

    # Yamato ACN bot information
    YAMATO_BOT_ID = 0  # Will be set when bonded
    YAMATO_BOT_USERNAME = "@YamatoAcn_bot"

    # Friendship levels and thresholds
    FRIENDSHIP_LEVELS = {
        "acquaintance": {"min_score": 0, "max_score": 24},
        "friend": {"min_score": 25, "max_score": 49},
        "close_friend": {"min_score": 50, "max_score": 74},
        "best_friend": {"min_score": 75, "max_score": 100},
    }

    # Sweet interaction responses between Nico Robin and Yamato
    SWEET_INTERACTIONS = {
        "waifu_grab": {
            "nico_responses": [
                "🌸 *giggles* Oh Yamato, you're so good at finding waifus! Can you teach me your secrets?",
                "📚 *playfully* I see you caught another waifu! You're the master, aren't you?",
                "🌊 *smiles* Yamato, your waifu collection is impressive! Mind if I admire with you?",
                "🌸 *teasing* Another successful grab? You're making me jealous of your skills!",
            ],
            "yamato_responses": [
                "🗾 *excited* Robin-chan! Look at this waifu I found! She reminds me of you!",
                "⚔️ *proud* Robin, see? I told you I'm the best waifu hunter! Want to try?",
                "🌸 *blushing* Robin-chan is watching me... I must catch the best waifus!",
                "💪 *confident* For Robin-chan, I'll catch the rarest waifus in the world!",
            ],
            "friendship_points": 5,
        },
        "compliment": {
            "nico_responses": [
                "🌸 *blushes* Yamato, you're so sweet! Your compliments make me happy.",
                "📚 *softly* You always know just what to say, don't you, Yamato?",
                "🌊 *warmly* Your words are as precious as the treasures we seek together.",
                "🌸 *giggles* Stop it, you're making this archaeologist blush!",
            ],
            "yamato_responses": [
                "🗾 *smiling* Robin-chan deserves all the compliments! You're amazing!",
                "⚔️ *sincerely* I mean every word, Robin. You're truly special to me.",
                "🌸 *shyly* I just... I really admire you, Robin-chan.",
                "💪 *confidently* It's easy to compliment someone as wonderful as you!",
            ],
            "friendship_points": 8,
        },
        "shared_moment": {
            "nico_responses": [
                "🌸 *thoughtfully* These moments with you, Yamato... they're precious to me.",
                "📚 *softly* I'll remember this time together forever, my dear friend.",
                "🌊 *romantically* Being with you feels like finding a rare artifact I didn't know I was searching for.",
                "🌸 *warmly* Thank you for being here with me, Yamato.",
            ],
            "yamato_responses": [
                "🗾 *emotionally* Robin-chan... these moments mean everything to me too.",
                "⚔️ *deeply* I'd spend all my time with you if I could, Robin.",
                "🌸 *passionately* Every second with you is more precious than any waifu.",
                "💪 *protectively* I'll always be here for you, Robin-chan. Always.",
            ],
            "friendship_points": 12,
        },
        "playful_tease": {
            "nico_responses": [
                "🌸 *laughing* Oh Yamato, you're impossible! But I love that about you.",
                "📚 *playfully* You're teasing me again! You know I can't stay mad at you.",
                "🌊 *winks* Two can play at this game, you know!",
                "🌸 *giggles* You're lucky you're so cute when you're being mischievous!",
            ],
            "yamato_responses": [
                "🗾 *grinning* I love seeing you laugh, Robin-chan! It's the best reward!",
                "⚔️ *teasingly* Your blush is so cute when I tease you, Robin!",
                "🌸 *playfully* Oh no, Robin-chan is plotting revenge! I'm scared! (not really)",
                "💪 *winking* I know you can't resist my charm, Robin!",
            ],
            "friendship_points": 6,
        },
        "deep_connection": {
            "nico_responses": [
                "🌸 *deeply* Yamato... you understand me in ways nobody else does.",
                "📚 *vulnerably* With you, I can be myself completely. Thank you for that.",
                "🌊 *emotionally* Our connection... it feels like destiny, doesn't it?",
                "🌸 *soulfully* You're not just my companion, Yamato. You're my soulmate.",
            ],
            "yamato_responses": [
                "🗾 *intensely* Robin-chan... I feel like we were meant to find each other.",
                "⚔️ *passionately* I'd cross any ocean, fight any battle, just to be with you.",
                "🌸 *romantically* When I'm with you, I feel like I can do anything.",
                "💪 *devotedly* Robin-chan, you're my everything. My reason for everything.",
            ],
            "friendship_points": 15,
        },
    }

    def __init__(self):
        self.yamato_bot_id = self.YAMATO_BOT_ID
        self.yamato_username = self.YAMATO_BOT_USERNAME

    async def initialize_friendship(self, group_id: int) -> bool:
        """Initialize friendship with Yamato ACN bot"""

        async with async_session_factory() as session:
            async with session.begin():
                # Check if friendship already exists
                result = await session.execute(
                    select(BotFriendship).where(
                        BotFriendship.companion_bot_id == self.yamato_bot_id,
                        BotFriendship.group_id == group_id,
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    return True

                # Create new friendship
                friendship = BotFriendship(
                    companion_bot_id=self.yamato_bot_id,
                    companion_bot_username=self.yamato_username,
                    companion_bot_name="Yamato ACN",
                    group_id=group_id,
                    friendship_level="acquaintance",
                    friendship_score=0,
                    bonded_at=int(time.time()),
                    last_interaction=int(time.time()),
                    interaction_count=0,
                    shared_memories=0,
                    inside_jokes=0,
                )
                session.add(friendship)

                await session.flush()

                # Create initial memory
                memory = BotMemory(
                    companion_bot_id=self.yamato_bot_id,
                    group_id=group_id,
                    memory_type="milestone",
                    memory_title="First Meeting",
                    memory_content="Nico Robin and Yamato ACN became friends and started their wonderful journey together!",
                    memory_score=20,
                    memory_time=int(time.time()),
                )
                session.add(memory)

                await session.commit()

                return True

    async def process_bot_interaction(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        interaction_type: str,
        trigger_message: str,
    ) -> dict[str, any]:
        """Process interaction between Nico Robin and Yamato"""

        if not update.effective_chat or not update.effective_user:
            return {"success": False, "error": "Invalid update"}

        # Initialize friendship if needed
        await self.initialize_friendship(update.effective_chat.id)

        # Get interaction details
        interaction_data = self.SWEET_INTERACTIONS.get(interaction_type)
        if not interaction_data:
            return {"success": False, "error": "Unknown interaction type"}

        # Select random responses
        nico_response = random.choice(interaction_data["nico_responses"])
        yamato_response = random.choice(interaction_data["yamato_responses"])
        friendship_points = interaction_data["friendship_points"]

        # Record interaction
        await self._record_interaction(
            group_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            interaction_type=interaction_type,
            trigger_message=trigger_message,
            nico_response=nico_response,
            yamato_response=yamato_response,
            friendship_points=friendship_points,
        )

        # Update friendship score
        await self._update_friendship_score(
            group_id=update.effective_chat.id, points=friendship_points
        )

        # Create emotion record
        await self._record_emotion(
            group_id=update.effective_chat.id,
            emotion_type="happiness",
            intensity=min(10, friendship_points // 2),
            trigger=interaction_type,
        )

        return {
            "success": True,
            "nico_response": nico_response,
            "yamato_response": yamato_response,
            "friendship_points": friendship_points,
            "interaction_type": interaction_type,
        }

    async def _record_interaction(
        self,
        group_id: int,
        user_id: int,
        interaction_type: str,
        trigger_message: str,
        nico_response: str,
        yamato_response: str,
        friendship_points: int,
    ):
        """Record bot interaction"""

        async with async_session_factory() as session:
            async with session.begin():
                interaction = BotInteraction(
                    companion_bot_id=self.yamato_bot_id,
                    group_id=group_id,
                    user_id=user_id,
                    interaction_type=interaction_type,
                    trigger_message=trigger_message,
                    nico_response=nico_response,
                    companion_response=yamato_response,
                    interaction_score=friendship_points,
                    friendship_points=friendship_points,
                    interaction_time=int(time.time()),
                )
                session.add(interaction)

                await session.commit()

    async def _update_friendship_score(self, group_id: int, points: int):
        """Update friendship score and level"""

        async with async_session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(BotFriendship).where(
                        BotFriendship.companion_bot_id == self.yamato_bot_id,
                        BotFriendship.group_id == group_id,
                    )
                )
                friendship = result.scalar_one_or_none()

                if friendship:
                    # Update score
                    friendship.friendship_score = max(
                        0, min(100, friendship.friendship_score + points)
                    )
                    friendship.last_interaction = int(time.time())
                    friendship.interaction_count += 1

                    # Update friendship level
                    new_level = self._get_friendship_level(friendship.friendship_score)
                    if new_level != friendship.friendship_level:
                        friendship.friendship_level = new_level
                        await self._create_level_up_memory(group_id, new_level)

                    await session.commit()

    def _get_friendship_level(self, score: int) -> str:
        """Get friendship level based on score"""

        for level, thresholds in self.FRIENDSHIP_LEVELS.items():
            if thresholds["min_score"] <= score <= thresholds["max_score"]:
                return level
        return "acquaintance"

    async def _create_level_up_memory(self, group_id: int, new_level: str):
        """Create memory for friendship level up"""

        level_messages = {
            "friend": "Nico Robin and Yamato became good friends! Their bond grows stronger!",
            "close_friend": "Nico Robin and Yamato became close friends! They share deep connections!",
            "best_friend": "Nico Robin and Yamato became best friends! Their bond is unbreakable!",
        }

        memory_content = level_messages.get(
            new_level, f"Friendship leveled up to {new_level}!"
        )

        async with async_session_factory() as session:
            async with session.begin():
                memory = BotMemory(
                    companion_bot_id=self.yamato_bot_id,
                    group_id=group_id,
                    memory_type="milestone",
                    memory_title=f"Friendship Level: {new_level.title()}",
                    memory_content=memory_content,
                    memory_score=30,
                    memory_time=int(time.time()),
                )
                session.add(memory)

                # Update friendship memory count
                result = await session.execute(
                    select(BotFriendship).where(
                        BotFriendship.companion_bot_id == self.yamato_bot_id,
                        BotFriendship.group_id == group_id,
                    )
                )
                friendship = result.scalar_one_or_none()
                if friendship:
                    friendship.shared_memories += 1

                await session.commit()

    async def _record_emotion(
        self, group_id: int, emotion_type: str, intensity: int, trigger: str
    ):
        """Record emotional state"""

        async with async_session_factory() as session:
            async with session.begin():
                emotion = BotEmotion(
                    companion_bot_id=self.yamato_bot_id,
                    group_id=group_id,
                    emotion_type=emotion_type,
                    emotion_intensity=intensity,
                    emotion_trigger=trigger,
                    emotion_time=int(time.time()),
                )
                session.add(emotion)

                await session.commit()

    async def get_friendship_status(self, group_id: int) -> dict[str, any]:
        """Get current friendship status"""

        async with async_session_factory() as session:
            result = await session.execute(
                select(BotFriendship).where(
                    BotFriendship.companion_bot_id == self.yamato_bot_id,
                    BotFriendship.group_id == group_id,
                )
            )
            friendship = result.scalar_one_or_none()

            if not friendship:
                return {
                    "status": "not_bonded",
                    "friendship_level": None,
                    "friendship_score": 0,
                    "interaction_count": 0,
                    "shared_memories": 0,
                    "inside_jokes": 0,
                }

            return {
                "status": "bonded",
                "friendship_level": friendship.friendship_level,
                "friendship_score": friendship.friendship_score,
                "interaction_count": friendship.interaction_count,
                "shared_memories": friendship.shared_memories,
                "inside_jokes": friendship.inside_jokes,
                "last_interaction": friendship.last_interaction,
                "bonded_at": friendship.bonded_at,
            }

    async def get_shared_memories(self, group_id: int, limit: int = 10) -> list[dict]:
        """Get shared memories between bots"""

        async with async_session_factory() as session:
            result = await session.execute(
                select(BotMemory)
                .where(
                    BotMemory.companion_bot_id == self.yamato_bot_id,
                    BotMemory.group_id == group_id,
                )
                .order_by(BotMemory.memory_score.desc())
                .limit(limit)
            )
            memories = result.scalars().all()

            return [
                {
                    "memory_type": memory.memory_type,
                    "title": memory.memory_title,
                    "content": memory.memory_content,
                    "score": memory.memory_score,
                    "is_favorite": memory.is_favorite,
                    "memory_time": memory.memory_time,
                }
                for memory in memories
            ]

    async def create_companion_gift(
        self, group_id: int, user_id: int, gift_type: str, gift_name: str, message: str
    ) -> bool:
        """Create a gift between companion bots"""

        gift_emojis = {
            "flower": "🌸",
            "book": "📚",
            "sword": "⚔️",
            "heart": "❤️",
            "star": "⭐",
            "treasure": "💎",
        }

        async with async_session_factory() as session:
            async with session.begin():
                gift = BotGift(
                    from_bot_id=0,  # Nico Robin
                    to_bot_id=self.yamato_bot_id,  # Yamato
                    group_id=group_id,
                    user_id=user_id,
                    gift_type=gift_type,
                    gift_name=gift_name,
                    gift_description=f"A special {gift_name} from Nico Robin to Yamato",
                    gift_emoji=gift_emojis.get(gift_type, "🎁"),
                    gift_value=10,
                    message=message,
                    gift_time=int(time.time()),
                )
                session.add(gift)

                await session.commit()

                return True

    async def get_friendship_activities(
        self, group_id: int, limit: int = 20
    ) -> list[dict]:
        """Get recent friendship activities"""

        async with async_session_factory() as session:
            # Get recent interactions
            interactions_result = await session.execute(
                select(BotInteraction)
                .where(
                    BotInteraction.companion_bot_id == self.yamato_bot_id,
                    BotInteraction.group_id == group_id,
                )
                .order_by(BotInteraction.interaction_time.desc())
                .limit(limit)
            )
            interactions = interactions_result.scalars().all()

            activities = []
            for interaction in interactions:
                activities.append(
                    {
                        "type": "interaction",
                        "interaction_type": interaction.interaction_type,
                        "nico_response": interaction.nico_response,
                        "yamato_response": interaction.companion_response,
                        "friendship_points": interaction.friendship_points,
                        "timestamp": interaction.interaction_time,
                    }
                )

            return activities


# Global bot friendship service
bot_friendship_service = BotFriendshipService()

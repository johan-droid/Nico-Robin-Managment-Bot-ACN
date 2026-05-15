from __future__ import annotations

import random

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from database import async_session_factory
from models.loyalty import LoyaltyPoints
from services.acn_service import ACNService


class NicoRobinFlirtingService:
    """Nico Robin's sophisticated flirting and social skills service"""

    def __init__(self):
        self.skill_categories = {
            "charming": {
                "name": "Charming Compliments",
                "description": "Elegant and sophisticated compliments",
                "difficulty": "easy",
                "success_rate": 0.85,
            },
            "intellectual": {
                "name": "Intellectual Banter",
                "description": "Smart and witty conversations",
                "difficulty": "medium",
                "success_rate": 0.75,
            },
            "mysterious": {
                "name": "Mysterious Allure",
                "description": "Enigmatic and intriguing interactions",
                "difficulty": "hard",
                "success_rate": 0.65,
            },
            "playful": {
                "name": "Playful Teasing",
                "description": "Light-hearted and fun interactions",
                "difficulty": "easy",
                "success_rate": 0.80,
            },
            "romantic": {
                "name": "Romantic Gestures",
                "description": "Deeply romantic and heartfelt moments",
                "difficulty": "medium",
                "success_rate": 0.70,
            },
            "confident": {
                "name": "Confident Advances",
                "description": "Bold and self-assured interactions",
                "difficulty": "hard",
                "success_rate": 0.60,
            },
        }

        # Load all flirting events from directory
        self.flirting_events = self._load_flirting_events()

    def _load_flirting_events(self) -> dict[str, list[dict]]:
        """Load all flirting events from the events directory"""
        events = {
            "charming": [
                {
                    "id": "charm_001",
                    "trigger_words": ["beautiful", "gorgeous", "pretty", "stunning"],
                    "responses": [
                        "🌸 *blushes slightly* Oh my... such sweet words coming from you? You have quite the way with words, don't you?",
                        "📚 *adjusts glasses* I must admit, your compliments are as rare as ancient artifacts - truly precious.",
                        "🌊 *smiles gently* You know, archaeologists say beauty is timeless... but your words make it feel present.",
                    ],
                    "success_response": "✨ *twirls hair playfully* You really know how to make a scholar feel special!",
                    "fail_response": "📖 *closes book* Perhaps we should stick to academic discussions...",
                    "points_earned": 5,
                    "skill_level": "beginner",
                },
                {
                    "id": "charm_002",
                    "trigger_words": ["smart", "intelligent", "clever", "brilliant"],
                    "responses": [
                        "🧠 *eyes light up* Intelligence is the most attractive quality, you know. Your mind must be a fascinating place to explore.",
                        "📚 *leans in closer* Tell me more about your thoughts... I could listen to you speak all day.",
                        "🌸 *giggles* You're making this historian blush! Your intellect is quite... impressive.",
                    ],
                    "success_response": "💫 *touches cheek* You have a way with words that rivals ancient poetry!",
                    "fail_response": "📖 *looks away* Maybe we should discuss something less... personal?",
                    "points_earned": 7,
                    "skill_level": "intermediate",
                },
            ],
            "intellectual": [
                {
                    "id": "intel_001",
                    "trigger_words": ["history", "knowledge", "learn", "study"],
                    "responses": [
                        "📚 *eyes sparkle* Oh, you appreciate knowledge too? We could spend hours discussing ancient civilizations!",
                        "🌊 *leans forward* The pursuit of knowledge is the most romantic journey of all. Shall we explore together?",
                        "🌸 *smiles knowingly* Someone who values learning... you're already capturing my interest.",
                    ],
                    "success_response": "🧠 *touches forehead* Your mind is as vast as the Grand Line itself!",
                    "fail_response": "📖 *adjusts glasses* Perhaps we should keep this strictly academic...",
                    "points_earned": 8,
                    "skill_level": "intermediate",
                },
                {
                    "id": "intel_002",
                    "trigger_words": ["mystery", "puzzle", "secret", "discover"],
                    "responses": [
                        "🔍 *eyes gleam* Mysteries are my specialty! Though I must admit, you're becoming quite the intriguing puzzle yourself.",
                        "📚 *whispers* Some secrets are meant to be shared... what do you want to discover first?",
                        "🌊 *smiles mysteriously* The greatest mystery is how you're making me feel...",
                    ],
                    "success_response": "✨ *leans closer* You and I could uncover the world's greatest secrets together!",
                    "fail_response": "📖 *looks thoughtful* Some mysteries are best left unsolved...",
                    "points_earned": 10,
                    "skill_level": "advanced",
                },
            ],
            "mysterious": [
                {
                    "id": "myst_001",
                    "trigger_words": ["who are you", "tell me", "your story"],
                    "responses": [
                        "🌸 *smiles enigmatically* My story is written in the pages of history... but perhaps you'd like to write a new chapter together?",
                        "📚 *looks away thoughtfully* Some things are better discovered slowly... like ancient ruins, or feelings.",
                        "🌊 *whispers* I am many things to many people... but to you? I could be anything you desire.",
                    ],
                    "success_response": "💫 *touches your hand* Some mysteries are meant to be shared with special people...",
                    "fail_response": "📖 *closes book* Not all stories are meant for every reader...",
                    "points_earned": 12,
                    "skill_level": "advanced",
                },
                {
                    "id": "myst_002",
                    "trigger_words": ["alone", "lonely", "by myself"],
                    "responses": [
                        "🌸 *softly* Even the most independent souls need company sometimes... and I find myself wanting yours.",
                        "📚 *closes book* Solitude is peaceful... but your presence makes it feel... incomplete.",
                        "🌊 *gently* You're never truly alone when someone is thinking of you... and I think of you often.",
                    ],
                    "success_response": "💝 *takes your hand* Let's be lonely together... or not lonely at all.",
                    "fail_response": "📖 *looks away* Perhaps some paths are meant to be walked alone...",
                    "points_earned": 15,
                    "skill_level": "expert",
                },
            ],
            "playful": [
                {
                    "id": "play_001",
                    "trigger_words": ["fun", "play", "game", "joke"],
                    "responses": [
                        "🌸 *laughs brightly* Fun? I haven't had genuine fun since... well, let's make some memories!",
                        "📚 *playfully* I may be a scholar, but even historians need to play! What's your game?",
                        "🌊 *winks* I know a game where we both win... interested in the rules?",
                    ],
                    "success_response": "🎉 *spins around* This is more exciting than discovering Poneglyphs!",
                    "fail_response": "📖 *adjusts glasses* Perhaps we should stick to more scholarly pursuits...",
                    "points_earned": 6,
                    "skill_level": "beginner",
                },
                {
                    "id": "play_002",
                    "trigger_words": ["tease", "joking", "kidding"],
                    "responses": [
                        "🌸 *playfully pouts* Hey! I can take a joke... but can you take my flirting back?",
                        "📚 *winks* Two can play at this game... though I must warn you, I'm quite clever.",
                        "🌊 *laughs* You're teasing me! That's bold... I like bold.",
                    ],
                    "success_response": "😏 *leans closer* Keep teasing me and see what happens...",
                    "fail_response": "📖 *looks unimpressed* Your jokes need... refinement.",
                    "points_earned": 8,
                    "skill_level": "intermediate",
                },
            ],
            "romantic": [
                {
                    "id": "rom_001",
                    "trigger_words": ["love", "heart", "feelings", "care"],
                    "responses": [
                        "🌸 *blushes deeply* Love... such a powerful word. Are you sure you know what you're awakening in me?",
                        "📚 *softly* The heart wants what it wants... and mine seems to want you.",
                        "🌊 *gently* Feelings are like ancient maps - leading us to treasures we never expected to find.",
                    ],
                    "success_response": "💝 *holds your hand* My heart hasn't felt this way since... well, ever.",
                    "fail_response": "📖 *looks away* Some feelings are too precious to share lightly...",
                    "points_earned": 20,
                    "skill_level": "expert",
                },
                {
                    "id": "rom_002",
                    "trigger_words": ["forever", "always", "never leave"],
                    "responses": [
                        "🌸 *tears form* Forever is a long time... but with you? It doesn't seem long enough.",
                        "📚 *whispers* I've spent my life seeking knowledge... but I'd spend forever seeking you.",
                        "🌊 *takes your hand* Always... that's a promise I'll keep until my last breath.",
                    ],
                    "success_response": "💞 *embraces you* Forever starts now, doesn't it?",
                    "fail_response": "📖 *looks sad* Forever is a heavy word... are you ready for that weight?",
                    "points_earned": 25,
                    "skill_level": "master",
                },
            ],
            "confident": [
                {
                    "id": "conf_001",
                    "trigger_words": ["strong", "powerful", "capable", "amazing"],
                    "responses": [
                        "🌸 *smiles confidently* I know my worth... but it's nice when someone else recognizes it too.",
                        "📚 *leans in* Power comes in many forms... but your admiration? That's the kind I crave.",
                        "🌊 *winks* Amazing? I try. Though you're making it hard to stay humble.",
                    ],
                    "success_response": "💪 *flexes playfully* Confidence looks good on me, but your attention looks better.",
                    "fail_response": "📖 *adjusts glasses* Modesty is a virtue, I suppose...",
                    "points_earned": 10,
                    "skill_level": "intermediate",
                },
                {
                    "id": "conf_002",
                    "trigger_words": ["want me", "desire", "attracted"],
                    "responses": [
                        "🌸 *steps closer* Desire is a dangerous game... but I've never been one to play it safe.",
                        "📚 *whispers* Wanting me is the first step... keeping me is the challenge. Are you ready?",
                        "🌊 *touches your face* The feeling is mutual... more than you could possibly imagine.",
                    ],
                    "success_response": "🔥 *pulls you close* Then have me... all of me.",
                    "fail_response": "📖 *steps back* Desire without wisdom is... unwise.",
                    "points_earned": 18,
                    "skill_level": "expert",
                },
            ],
        }

        return events

    async def process_flirting_attempt(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_text: str,
        target_user_id: int | None = None,
    ) -> dict[str, any]:
        """Process a flirting attempt and return response"""

        if not update.effective_user or not update.effective_chat:
            return {"success": False, "error": "Invalid update"}

        # Check if user is ACN member
        if not await ACNService.is_acn_member(update.effective_user.id):
            return {"success": False, "error": "ACN members only"}

        # Find matching event
        matched_event = self._find_matching_event(message_text)

        if not matched_event:
            return {
                "success": False,
                "response": "📖 *adjusts glasses* I'm not quite sure how to respond to that... perhaps try something more romantic?",
            }

        # Calculate success based on skill level and user stats
        success = await self._calculate_flirting_success(
            update.effective_user.id, update.effective_chat.id, matched_event
        )

        # Get response
        if success:
            response = random.choice(matched_event["responses"])
            success_response = matched_event["success_response"]
            points = matched_event["points_earned"]
        else:
            response = random.choice(
                matched_event["responses"][:2]
            )  # Use first 2 as fallback
            success_response = matched_event["fail_response"]
            points = 0

        # Award loyalty points if successful
        if success and points > 0:
            await self._award_flirting_points(
                update.effective_user.id,
                update.effective_chat.id,
                points,
                matched_event["id"],
            )

        return {
            "success": success,
            "response": response,
            "success_response": success_response,
            "points_earned": points,
            "event_id": matched_event["id"],
            "category": self._get_event_category(matched_event["id"]),
        }

    def _find_matching_event(self, message_text: str) -> dict | None:
        """Find the best matching flirting event"""
        message_lower = message_text.lower()
        best_match = None
        best_score = 0

        for _category, events in self.flirting_events.items():
            for event in events:
                score = 0
                for trigger_word in event["trigger_words"]:
                    if trigger_word.lower() in message_lower:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_match = event

        return best_match if best_score > 0 else None

    def _get_event_category(self, event_id: str) -> str:
        """Get the category of an event by its ID"""
        for category, events in self.flirting_events.items():
            for event in events:
                if event["id"] == event_id:
                    return category
        return "unknown"

    async def _calculate_flirting_success(
        self, user_id: int, group_id: int, event: dict
    ) -> bool:
        """Calculate if flirting attempt succeeds based on user stats and event difficulty"""

        try:
            async with async_session_factory() as session:
                # Get user's loyalty points
                loyalty_points = await session.execute(
                    select(LoyaltyPoints).where(
                        LoyaltyPoints.user_id == user_id,
                        LoyaltyPoints.group_id == group_id,
                    )
                )
                points_record = loyalty_points.scalar_one_or_none()

                user_points = points_record.points if points_record else 0
                user_rank = points_record.rank if points_record else "Crew Member"

                # Base success rate from event
                base_success = self.skill_categories[
                    self._get_event_category(event["id"])
                ]["success_rate"]

                # Modify based on user rank and points
                rank_bonus = {
                    "Crew Member": 0.0,
                    "Ensign": 0.05,
                    "Lieutenant": 0.10,
                    "Commander": 0.15,
                    "Captain": 0.20,
                    "Commodore": 0.25,
                    "Rear Admiral": 0.30,
                    "Vice Admiral": 0.35,
                    "Fleet Admiral": 0.40,
                }.get(user_rank, 0.0)

                # Points bonus (capped at 20%)
                points_bonus = min(user_points / 1000, 0.20)

                # Random factor
                random_factor = random.uniform(-0.1, 0.1)

                # Calculate final success rate
                final_success_rate = (
                    base_success + rank_bonus + points_bonus + random_factor
                )
                final_success_rate = max(
                    0.1, min(0.95, final_success_rate)
                )  # Clamp between 10% and 95%

                return random.random() < final_success_rate

        except Exception:
            # Default to base success rate if error
            return random.random() < event.get("success_rate", 0.7)

    async def _award_flirting_points(
        self, user_id: int, group_id: int, points: int, event_id: str
    ):
        """Award loyalty points for successful flirting"""
        try:
            import structlog

            from services.acn_service import ACNService

            logger = structlog.get_logger(__name__)

            async with async_session_factory() as session:
                async with session.begin():
                    await ACNService.add_loyalty_points(
                        session=session,
                        user_id=user_id,
                        group_id=group_id,
                        points=points,
                        activity_type="flirting",
                        action=f"successful_flirt_{event_id}",
                        metadata=f"flirting_event_id: {event_id}",
                    )
        except Exception as e:
            import structlog

            logger = structlog.get_logger(__name__)
            logger.error("flirting_award_error", error=str(e))

    def get_flirting_stats(self, user_id: int, group_id: int) -> dict[str, any]:
        """Get user's flirting statistics"""
        # This would be implemented with actual database queries
        return {
            "total_attempts": 0,
            "successful_flirts": 0,
            "favorite_category": "charming",
            "highest_skill_used": "beginner",
            "points_earned": 0,
            "success_rate": 0.0,
        }

    def get_available_categories(self) -> dict[str, dict]:
        """Get all available flirting categories"""
        return self.skill_categories

    def get_category_events(self, category: str) -> list[dict]:
        """Get all events in a specific category"""
        return self.flirting_events.get(category, [])

    def get_random_flirt_line(self, category: str | None = None) -> str:
        """Get a random flirt line for testing"""
        if category and category in self.flirting_events:
            events = self.flirting_events[category]
        else:
            # Random category
            category = random.choice(list(self.flirting_events.keys()))
            events = self.flirting_events[category]

        if events:
            event = random.choice(events)
            return random.choice(event["responses"])

        return "🌸 *smiles mysteriously* Perhaps you'd like to get to know me better?"


# Global flirting service instance
flirting_service = NicoRobinFlirtingService()


async def process_flirting_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_text: str,
    target_user_id: int | None = None,
) -> dict[str, any]:
    """Process flirting command and return response"""
    return await flirting_service.process_flirting_attempt(
        update, context, message_text, target_user_id
    )


def get_flirting_service() -> NicoRobinFlirtingService:
    """Get the global flirting service instance"""
    return flirting_service

"""
Romantic flirting events for Nico Robin
Deeply romantic and heartfelt interactions
"""

ROMANTIC_EVENTS = [
    {
        "id": "rom_003",
        "trigger_words": ["heart", "love", "romance", "passion"],
        "responses": [
            "❤️ *holds chest* My heart... it's beating so fast when you're near. Is this what love feels like?",
            "📚 *emotionally* I've read about love in ancient texts, but nothing prepared me for how you make me feel.",
            "🌸 *deeply* Love is the greatest treasure... and I think I've found it with you.",
        ],
        "success_response": "💞 *takes your hand* My heart is yours... completely.",
        "fail_response": "📖 *looks away* Love is dangerous... it leads to pain.",
        "points_earned": 20,
        "skill_level": "expert",
    },
    {
        "id": "rom_004",
        "trigger_words": ["kiss", "lips", "touch", "embrace"],
        "responses": [
            "💋 *blushes deeply* You want to kiss me? I've never... but with you, I want to.",
            "📚 *softly* Your lips... I wonder how they would feel against mine.",
            "🌸 *romantically* Your touch sets me on fire... in the best possible way.",
        ],
        "success_response": "💏 *leans in* Kiss me... please.",
        "fail_response": "📖 *steps back* Physical intimacy complicates things...",
        "points_earned": 18,
        "skill_level": "expert",
    },
    {
        "id": "rom_005",
        "trigger_words": ["marry", "wedding", "wife", "husband"],
        "responses": [
            "💍 *shocked* Marry you? I... I've never thought about marriage before. But with you? Maybe.",
            "📚 *romantically* A lifetime with you... that's the greatest adventure I could imagine.",
            "🌸 *dreamily* Being your wife... I could get used to that sound.",
        ],
        "success_response": "💑 *gets on one knee* Will you marry me?",
        "fail_response": "📖 *shakes head* Marriage is... serious business.",
        "points_earned": 25,
        "skill_level": "master",
    },
    {
        "id": "rom_006",
        "trigger_words": ["together", "always", "never leave"],
        "responses": [
            "🌸 *emotionally* Always... I want to be with you always, in every way possible.",
            "📚 *romantically* Never leave? I couldn't bear to lose you now that I've found you.",
            "🌊 *passionately* Together forever... that's the only future I want now.",
        ],
        "success_response": "🔗 *holds tightly* Together... always and forever.",
        "fail_response": "📖 *worried* Forever is a very long time...",
        "points_earned": 22,
        "skill_level": "master",
    },
    {
        "id": "rom_007",
        "trigger_words": ["soulmate", "destined", "meant to be"],
        "responses": [
            "👥 *deeply* Soulmate... I've heard of such things, but I never believed until I met you.",
            "📚 *romantically* We were meant to be... I feel it in every part of my being.",
            "🌸 *passionately* Fate brought us together... and I'll fight destiny to keep us that way.",
        ],
        "success_response": "💫 *soulfully* Our souls were made for each other.",
        "fail_response": "📖 *shakes head* Soulmates are... romantic nonsense.",
        "points_earned": 24,
        "skill_level": "master",
    },
    {
        "id": "rom_008",
        "trigger_words": ["intimate", "close", "personal", "private"],
        "responses": [
            "🌸 *vulnerably* Being intimate with you scares me... but I want to overcome that fear.",
            "📚 *softly* I've never been this close to anyone... it's both terrifying and wonderful.",
            "🌊 *romantically* Let me be close to you... in every way possible.",
        ],
        "success_response": "💝 *embraces completely* Let me be everything to you.",
        "fail_response": "📖 *guards herself* Intimacy requires trust... I'm not ready.",
        "points_earned": 19,
        "skill_level": "expert",
    },
    {
        "id": "rom_009",
        "trigger_words": ["devotion", "dedication", "commitment"],
        "responses": [
            "💝 *emotionally* I'm devoted to you... completely, utterly, irrevocably.",
            "📚 *romantically* My dedication to you is stronger than my dedication to history itself.",
            "🌸 *passionately* I commit my heart, my soul, my entire being to you.",
        ],
        "success_response": "💍 *offers ring* I'm yours... forever.",
        "fail_response": "📖 *worried* Commitment is... dangerous in our world.",
        "points_earned": 23,
        "skill_level": "master",
    },
    {
        "id": "rom_010",
        "trigger_words": ["passion", "desire", "lust", "craving"],
        "responses": [
            "🔥 *breathlessly* The passion I feel for you... it consumes me completely.",
            "📚 *intensely* I desire you more than knowledge, more than history, more than anything.",
            "🌸 *romantically* My body craves yours... my soul needs yours... I'm lost without you.",
        ],
        "success_response": "🔥 *pulls close* Let the passion consume us both.",
        "fail_response": "📖 *steps back* Passion without control is... dangerous.",
        "points_earned": 21,
        "skill_level": "expert",
    },
]

# Extended romantic events
EXTENDED_ROMANTIC_EVENTS = [
    {
        "id": "rom_011",
        "trigger_words": ["vow", "promise", "pledge", "oath"],
        "responses": [
            "🙏 *solemnly* I vow to love you, protect you, and cherish you for all of my days.",
            "📚 *romantically* I promise to be yours completely, in this life and any that may follow.",
            "🌸 *emotionally* I pledge my heart to you... now and forever, until my last breath.",
        ],
        "success_response": "🙏 *takes vow* Before all witnesses, I am yours.",
        "fail_response": "📖 *serious* Vows should not be made lightly...",
        "points_earned": 25,
        "skill_level": "master",
    },
    {
        "id": "rom_012",
        "trigger_words": ["sunset", "sunrise", "dawn", "twilight"],
        "responses": [
            "🌅 *romantically* I want to watch every sunrise and sunset with you by my side.",
            "🌸 *dreamily* The dawn breaks... but with you, every day feels like a new beginning.",
            "📚 *passionately* In the twilight hours, I find myself thinking only of you.",
        ],
        "success_response": "🌅 *holds close* Let's watch all our sunsets together.",
        "fail_response": "📖 *looks away* Time passes... we should focus on the present.",
        "points_earned": 20,
        "skill_level": "expert",
    },
    {
        "id": "rom_013",
        "trigger_words": ["poem", "song", "melody", "music"],
        "responses": [
            "🎵 *softly* You inspire poetry in my soul... words I never knew I could write.",
            "📚 *romantically* My heart sings when you're near... a melody only you can hear.",
            "🌸 *poetically* You are the poem I've been waiting to write my entire life.",
        ],
        "success_response": "🎵 *sings softly* Our love song... perfect harmony.",
        "fail_response": "📖 *serious* Poetry and songs are... frivolous.",
        "points_earned": 18,
        "skill_level": "expert",
    },
    {
        "id": "rom_014",
        "trigger_words": ["home", "belong", "family", "together"],
        "responses": [
            "🏠 *emotionally* With you, I finally feel like I've found my home.",
            "📚 *romantically* I belong with you... you're the family I've always wanted.",
            "🌸 *warmly* Together, we're not just lovers... we're home to each other.",
        ],
        "success_response": "🏡 *takes your hand* Welcome home, my love.",
        "fail_response": "📖 *guarded* Home is... complicated for people like us.",
        "points_earned": 22,
        "skill_level": "master",
    },
    {
        "id": "rom_015",
        "trigger_words": ["eternity", "infinity", "endless", "timeless"],
        "responses": [
            "♾️ *eternally* I want to love you for eternity... and even that wouldn't be enough time.",
            "📚 *romantically* My love for you is infinite... boundless, endless, timeless.",
            "🌸 *passionately* In your arms, time stands still... and infinity feels too short.",
        ],
        "success_response": "♾️ *holds forever* Our love transcends time itself.",
        "fail_response": "📖 *shakes head* Infinity is... a concept, not reality.",
        "points_earned": 30,
        "skill_level": "master",
    },
]

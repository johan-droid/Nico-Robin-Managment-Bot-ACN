"""
Mysterious flirting events for Nico Robin
Enigmatic and intriguing interactions
"""

MYSTERIOUS_EVENTS = [
    {
        "id": "myst_003",
        "trigger_words": ["secret", "hidden", "private", "confidential"],
        "responses": [
            "🌸 *whispers* I have many secrets... but you're the one I want to share them with.",
            "📚 *mysteriously* Everyone has hidden depths... yours seem particularly fascinating to explore.",
            "🌊 *enigmatically* Some secrets are meant to be shared... what do you want to know first?",
        ],
        "success_response": "🔐 *leans close* My secrets are yours now...",
        "fail_response": "📖 *looks away* Some secrets should remain buried...",
        "points_earned": 12,
        "skill_level": "advanced",
    },
    {
        "id": "myst_004",
        "trigger_words": ["past", "history", "before", "previous"],
        "responses": [
            "🌸 *thoughtfully* My past is complicated... full of things I can't easily explain.",
            "📚 *vulnerably* Everyone has a history... mine led me to you, so I can't regret it.",
            "🌊 *softly* The past made me who I am... but with you, I feel like I could be someone new.",
        ],
        "success_response": "🕰️ *takes your hand* Let's create a new future together.",
        "fail_response": "📖 *shakes head* The past is painful... let's not dwell there.",
        "points_earned": 13,
        "skill_level": "advanced",
    },
    {
        "id": "myst_005",
        "trigger_words": ["destiny", "fate", "meant to be", "meant to meet"],
        "responses": [
            "🌸 *romantically* I don't believe in fate... but meeting you makes me reconsider everything.",
            "📚 *deeply* Destiny is written in the stars... and I think ours were aligned.",
            "🌊 *mysteriously* Some things are meant to be... us, for instance.",
        ],
        "success_response": "⭐ *looks up* The stars brought us together...",
        "fail_response": "📖 *looks down* We make our own destiny... nothing is predetermined.",
        "points_earned": 14,
        "skill_level": "expert",
    },
    {
        "id": "myst_006",
        "trigger_words": ["dark", "shadows", "night", "darkness"],
        "responses": [
            "🌸 *softly* I've spent time in darkness... but with you, even shadows feel warm.",
            "📚 *mysteriously* The night has secrets... and you're making me want to share mine.",
            "🌊 *romantically* In the darkness, all masks fall away... and you see the real me.",
        ],
        "success_response": "🌙 *whispers* Let's get lost in the darkness together...",
        "fail_response": "📖 *serious* Darkness hides many dangers... we should be careful.",
        "points_earned": 15,
        "skill_level": "expert",
    },
    {
        "id": "myst_007",
        "trigger_words": ["unknown", "mystery", "puzzle", "riddle"],
        "responses": [
            "🔍 *eyes sparkle* I love mysteries! Though you're becoming the most intriguing puzzle I've ever encountered.",
            "📚 *thoughtfully* Life is a riddle... and I think you might be my answer.",
            "🌸 *playfully* Want to solve the mystery of me? It might take a lifetime... but I suspect you're up for the challenge.",
        ],
        "success_response": "🧩 *smiles* Let's solve each other's puzzles together.",
        "fail_response": "📖 *guarded* Some mysteries are best left unsolved.",
        "points_earned": 16,
        "skill_level": "expert",
    },
    {
        "id": "myst_008",
        "trigger_words": ["invisible", "unseen", "hidden", "disappear"],
        "responses": [
            "🌸 *softly* I've spent my life being invisible... but you see me. Truly see me.",
            "📚 *vulnerably* I can disappear when I need to... but I never want to disappear from you.",
            "🌊 *romantically* Even when I'm invisible, I'm always thinking of you... watching over you.",
        ],
        "success_response": "👁️ *appears suddenly* I'll always be here for you to see.",
        "fail_response": "📖 *fades slightly* Sometimes being invisible is safer...",
        "points_earned": 17,
        "skill_level": "master",
    },
    {
        "id": "myst_009",
        "trigger_words": ["magic", "supernatural", "impossible", "miracle"],
        "responses": [
            "🌸 *wonderingly* You make me believe in magic... things I thought were impossible.",
            "📚 *romantically* Meeting you was a miracle... the best thing that ever happened to me.",
            "🌊 *mysteriously* Some things defy explanation... us, for instance.",
        ],
        "success_response": "✨ *glows* Our love is the greatest magic of all.",
        "fail_response": "📖 *serious* Magic isn't real... only hard work and sacrifice.",
        "points_earned": 18,
        "skill_level": "master",
    },
    {
        "id": "myst_010",
        "trigger_words": ["whispers", "quiet", "silent", "hush"],
        "responses": [
            "🌸 *whispers back* Some things are best said quietly... like how much I care about you.",
            "📚 *softly* In the silence between words... that's where true feelings live.",
            "🌊 *romantically* Let me whisper secrets to you that I've never told anyone...",
        ],
        "success_response": "🤫 *leans close* Our secrets are safe between us.",
        "fail_response": "📖 *looks away* Some things should remain unspoken.",
        "points_earned": 19,
        "skill_level": "master",
    },
]

# Extended mysterious events
EXTENDED_MYSTERIOUS_EVENTS = [
    {
        "id": "myst_011",
        "trigger_words": ["ghost", "spirit", "haunting", "apparition"],
        "responses": [
            "👻 *playfully* I could haunt you... but I'd rather be your living, breathing reality.",
            "🌸 *mysteriously* Sometimes I feel like a ghost... watching from the shadows. But you make me want to be seen.",
            "📚 *romantically* You haunt my thoughts... in the most wonderful way.",
        ],
        "success_response": "👻 *appears behind* Boo! I'm here to stay.",
        "fail_response": "📖 *fades* Ghosts belong in the past...",
        "points_earned": 16,
        "skill_level": "expert",
    },
    {
        "id": "myst_012",
        "trigger_words": ["veil", "mask", "disguise", "hidden identity"],
        "responses": [
            "🎭 *removes mask* I wear many masks... but with you, I want to show my true face.",
            "🌸 *vulnerably* The veil between us is so thin... I can almost see your soul.",
            "📚 *romantically* Behind every mask is a real person... let me show you mine.",
        ],
        "success_response": "🎭 *drops all masks* This is the real me... all of me.",
        "fail_response": "📖 *pulls mask up* Some faces should remain hidden.",
        "points_earned": 17,
        "skill_level": "expert",
    },
    {
        "id": "myst_013",
        "trigger_words": ["labyrinth", "maze", "lost", "found"],
        "responses": [
            "🌸 *softly* I was lost for so long... then I found you. Now I'm found forever.",
            "📚 *romantically* Life is a labyrinth... but with you, I've found my way home.",
            "🌊 *mysteriously* Getting lost with you sounds like the best adventure ever.",
        ],
        "success_response": "🗺️ *takes your hand* Let's get lost together... and found.",
        "fail_response": "📖 *looks away* Getting lost is dangerous... we might not find our way back.",
        "points_earned": 18,
        "skill_level": "master",
    },
    {
        "id": "myst_014",
        "trigger_words": ["prophecy", "prediction", "vision", "foresee"],
        "responses": [
            "🔮 *gazes into eyes* I see a future... with you in it. Always.",
            "🌸 *romantically* I had a vision once... of someone who would understand me. That someone is you.",
            "📚 *mysteriously* The ancient prophecies spoke of a meeting... ours was foretold.",
        ],
        "success_response": "👁️ *closes eyes* Our destiny is sealed... together.",
        "fail_response": "📖 *shakes head* Prophecies are dangerous... they give false hope.",
        "points_earned": 19,
        "skill_level": "master",
    },
    {
        "id": "myst_015",
        "trigger_words": ["eternal", "immortal", "forever young", "timeless"],
        "responses": [
            "🌸 *eternally* With you, I feel timeless... as if we could love forever and it would never be enough.",
            "📚 *romantically* I've studied ancient civilizations... they all crumbled. But our love? That feels eternal.",
            "🌊 *deeply* Time has no meaning when I'm with you... we exist outside its grasp.",
        ],
        "success_response": "⏳ *holds forever* Our love transcends time itself.",
        "fail_response": "📖 *looks sad* Nothing lasts forever... especially not happiness.",
        "points_earned": 25,
        "skill_level": "master",
    },
]

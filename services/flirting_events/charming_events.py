"""
Charming flirting events for Nico Robin
Elegant and sophisticated compliments and interactions
"""

CHARMING_EVENTS = [
    {
        "id": "charm_003",
        "trigger_words": ["eyes", "beautiful eyes", "pretty eyes"],
        "responses": [
            "🌸 *blushes and looks away* My eyes? They say the eyes are windows to the soul... yours must be quite beautiful then.",
            "📚 *adjusts glasses thoughtfully* You're looking into my eyes? I hope you like what you see... because I'm certainly enjoying yours.",
            "🌊 *gently* Your gaze is captivating... it's making this historian forget her research.",
        ],
        "success_response": "✨ *leans closer* Your eyes tell stories I'd love to read...",
        "fail_response": "📖 *looks down* Perhaps we should focus on the conversation instead?",
        "points_earned": 6,
        "skill_level": "beginner",
    },
    {
        "id": "charm_004",
        "trigger_words": ["smile", "laugh", "happy"],
        "responses": [
            "🌸 *smiles back* Your smile could light up the darkest archaeological site!",
            "📚 *giggles* I don't laugh often, but you make it feel natural.",
            "🌊 *warmly* Seeing you happy makes me feel... content. That's rare for me.",
        ],
        "success_response": "💫 *touches her own face* You make me want to smile more often!",
        "fail_response": "📖 *looks serious* Happiness is fleeting... we should treasure it.",
        "points_earned": 7,
        "skill_level": "beginner",
    },
    {
        "id": "charm_005",
        "trigger_words": ["voice", "sound", "speak"],
        "responses": [
            "🌸 *softly* Your voice is like music... I could listen to you read ancient texts all day.",
            "📚 *leans in* The way you speak... it's quite captivating. Tell me more.",
            "🌊 *whispers* Your voice makes me feel... things I haven't felt before.",
        ],
        "success_response": "💝 *takes your hand* Keep talking... I'm listening to every word.",
        "fail_response": "📖 *adjusts glasses* Perhaps we should communicate through writing instead?",
        "points_earned": 8,
        "skill_level": "intermediate",
    },
    {
        "id": "charm_006",
        "trigger_words": ["gentle", "kind", "sweet"],
        "responses": [
            "🌸 *softly* Kindness is a rare treasure in this world... and you seem to have it in abundance.",
            "📚 *blushes* You're gentle with me... that's not something I'm used to.",
            "🌊 *warmly* Your sweetness is disarming... I'm usually more guarded.",
        ],
        "success_response": "🌸 *hugs gently* Your kindness makes me want to be vulnerable with you.",
        "fail_response": "📖 *looks away* Gentleness can be a weakness in our world...",
        "points_earned": 9,
        "skill_level": "intermediate",
    },
    {
        "id": "charm_007",
        "trigger_words": ["perfect", "flawless", "ideal"],
        "responses": [
            "🌸 *laughs softly* Perfect? Oh my... nobody's perfect. But you're making me feel like I could be.",
            "📚 *thoughtfully* Perfection is an illusion... but your admiration feels very real.",
            "🌊 *blushes* You think I'm perfect? That's... quite a compliment coming from someone like you.",
        ],
        "success_response": "💫 *twirls* If I'm perfect in your eyes, then that's all that matters!",
        "fail_response": "📖 *shakes head* Perfection is impossible... we should embrace imperfection.",
        "points_earned": 10,
        "skill_level": "intermediate",
    },
    {
        "id": "charm_008",
        "trigger_words": ["special", "unique", "different"],
        "responses": [
            "🌸 *eyes sparkle* Special? You see something in me that others don't, don't you?",
            "📚 *leans closer* Different can be dangerous... but with you? It feels exciting.",
            "🌊 *smiles mysteriously* I've always been different... but you make me feel special for it.",
        ],
        "success_response": "💝 *takes your hand* You're special too... that's why we understand each other.",
        "fail_response": "📖 *looks away* Being different has brought me nothing but pain...",
        "points_earned": 11,
        "skill_level": "advanced",
    },
    {
        "id": "charm_009",
        "trigger_words": ["admire", "look up to", "respect"],
        "responses": [
            "🌸 *surprised* You admire me? I'm just doing what I must... but your respect means everything.",
            "📚 *softly* Respect is earned, not given... yet you give it so freely. Why?",
            "🌊 *humbly* I'm not worthy of your admiration... but I'll try to be.",
        ],
        "success_response": "🌟 *bows slightly* Your respect inspires me to be better.",
        "fail_response": "📖 *looks down* I don't deserve your admiration... really.",
        "points_earned": 12,
        "skill_level": "advanced",
    },
    {
        "id": "charm_010",
        "trigger_words": ["dream", "fantasy", "imagine"],
        "responses": [
            "🌸 *dreamily* You're in my dreams already... did you know that?",
            "📚 *whispers* My fantasies usually involve ancient ruins... but now they involve you.",
            "🌊 *romantically* Imagine us... exploring the world together, discovering its secrets... and each other.",
        ],
        "success_response": "💫 *closes eyes* Let's dream together... reality can wait.",
        "fail_response": "📖 *opens eyes* Dreams are dangerous... they give us hope we shouldn't have.",
        "points_earned": 15,
        "skill_level": "expert",
    },
]

# Additional charming events for variety
EXTENDED_CHARMING_EVENTS = [
    {
        "id": "charm_011",
        "trigger_words": ["touch", "hold", "embrace"],
        "responses": [
            "🌸 *shivers slightly* Your touch... it's electric. I'm not used to being touched so gently.",
            "📚 *leans into touch* Don't stop... I've been lonely for so long.",
            "🌊 *closes eyes* Your hands are warm... I could stay like this forever.",
        ],
        "success_response": "💞 *holds tighter* I never want to let go.",
        "fail_response": "📖 *steps back* Physical contact complicates things...",
        "points_earned": 13,
        "skill_level": "advanced",
    },
    {
        "id": "charm_012",
        "trigger_words": ["protect", "keep safe", "guard"],
        "responses": [
            "🌸 *softly* You want to protect me? That's... sweet. I'm usually the one protecting others.",
            "📚 *vulnerable* I've been protecting myself for so long... letting someone else protect me feels... nice.",
            "🌊 *trustingly* With you guarding me, maybe I could finally rest.",
        ],
        "success_response": "🛡️ *leans on you* I trust you to keep me safe.",
        "fail_response": "📖 *stands tall* I can protect myself... but thank you for offering.",
        "points_earned": 14,
        "skill_level": "expert",
    },
    {
        "id": "charm_013",
        "trigger_words": ["future", "tomorrow", "together"],
        "responses": [
            "🌸 *hopefully* A future with you in it... that's something I dare to dream about.",
            "📚 *romantically* Tomorrow isn't promised... but if it comes, I want it to come with you.",
            "🌊 *takes your hand* Together... I like the sound of that. Very much.",
        ],
        "success_response": "🌅 *looks at horizon* Our future starts now, doesn't it?",
        "fail_response": "📖 *looks down* The future is uncertain... we shouldn't make promises.",
        "points_earned": 16,
        "skill_level": "expert",
    },
    {
        "id": "charm_014",
        "trigger_words": ["miss", "think about", "can't stop"],
        "responses": [
            "🌸 *blushes* You think about me? I... I think about you too. More than I should.",
            "📚 *confesses* I can't focus on my studies... my mind keeps wandering to you.",
            "🌊 *whispers* I miss you even when you're right here... because I want more of you.",
        ],
        "success_response": "💝 *holds face* I'm yours... completely.",
        "fail_response": "📖 *looks away* Obsession is dangerous... we should be careful.",
        "points_earned": 17,
        "skill_level": "master",
    },
    {
        "id": "charm_015",
        "trigger_words": ["complete", "whole", "everything"],
        "responses": [
            "🌸 *deeply* You make me feel complete... like I've been missing a piece of myself my whole life.",
            "📚 *emotionally* With you, I'm not just Nico Robin, archaeologist... I'm whole.",
            "🌊 *passionately* You're everything I never knew I needed... and everything I've always wanted.",
        ],
        "success_response": "💫 *embraces completely* We're whole together.",
        "fail_response": "📖 *shakes head* Completion is an illusion... we're always incomplete.",
        "points_earned": 20,
        "skill_level": "master",
    },
]

"""
Intellectual flirting events for Nico Robin
Smart and witty conversations and interactions
"""

INTELLECTUAL_EVENTS = [
    {
        "id": "intel_003",
        "trigger_words": ["read", "books", "library", "knowledge"],
        "responses": [
            "📚 *eyes light up* You appreciate books too? We could spend nights in the library together... discussing ancient texts.",
            "🌸 *smiles* I've read thousands of books, but none compare to the story I want to write with you.",
            "🌊 *thoughtfully* Knowledge is power... but sharing it with someone like you? That's true wisdom.",
        ],
        "success_response": "🧠 *leans closer* Let's get lost in knowledge together.",
        "fail_response": "📖 *closes book* Perhaps some knowledge is best kept to oneself.",
        "points_earned": 9,
        "skill_level": "intermediate",
    },
    {
        "id": "intel_004",
        "trigger_words": ["archaeology", "history", "ancient", "ruins"],
        "responses": [
            "📚 *passionately* Archaeology is my life's work... but you're making me want to discover something new: you.",
            "🌸 *dreamily* Ancient ruins hold secrets... but your eyes hold mysteries I want to uncover.",
            "🌊 *romantically* I've explored many historical sites... but the most fascinating discovery would be you.",
        ],
        "success_response": "🏛️ *takes your hand* Let's explore history together.",
        "fail_response": "📖 *looks serious* History is important work, not entertainment.",
        "points_earned": 11,
        "skill_level": "advanced",
    },
    {
        "id": "intel_005",
        "trigger_words": ["smart", "clever", "brilliant", "genius"],
        "responses": [
            "🧠 *impressed* Your intellect is... captivating. I haven't met anyone who challenges my mind like you do.",
            "📚 *leans in* Brilliance is attractive... and you, my dear, are absolutely radiant.",
            "🌸 *blushes* You're making this historian feel... things I've only read about in books.",
        ],
        "success_response": "✨ *touches forehead* Your mind is as vast as the Grand Line itself!",
        "fail_response": "📖 *adjusts glasses* Intelligence without wisdom is... incomplete.",
        "points_earned": 10,
        "skill_level": "intermediate",
    },
    {
        "id": "intel_006",
        "trigger_words": ["debate", "discuss", "argue", "opinion"],
        "responses": [
            "📚 *excitedly* A debate with you? I'd love that! Though I have a feeling I'd enjoy losing to you.",
            "🌸 *playfully* I could argue with you all night... though I have a suspicion we'd end up agreeing on the important things.",
            "🌊 *intellectually* Your opinions fascinate me... even when we disagree, your logic is compelling.",
        ],
        "success_response": "🎯 *smiles* Let the battle of wits begin!",
        "fail_response": "📖 *shakes head* Some discussions are pointless... let's not waste time.",
        "points_earned": 12,
        "skill_level": "advanced",
    },
    {
        "id": "intel_007",
        "trigger_words": ["learn", "teach", "show me", "explain"],
        "responses": [
            "📚 *enthusiastically* I'd love to teach you! Though I suspect you'd be an excellent student... in more ways than one.",
            "🌸 *softly* There's so much I want to show you... not just about history, but about... us.",
            "🌊 *romantically* Let me teach you about ancient love stories... then we can write our own.",
        ],
        "success_response": "🎓 *takes your hand* Class is in session... and you're my favorite subject.",
        "fail_response": "📖 *looks away* Some lessons are better learned alone.",
        "points_earned": 13,
        "skill_level": "advanced",
    },
    {
        "id": "intel_008",
        "trigger_words": ["understand", "comprehend", "get me"],
        "responses": [
            "🧠 *thoughtfully* You understand me? That's... rare. Most people see the scholar, not the woman.",
            "📚 *vulnerably* You see past my knowledge to who I really am... how did you do that?",
            "🌸 *deeply* Being understood by you is more intoxicating than any ancient wine.",
        ],
        "success_response": "💝 *embraces* Finally... someone who truly sees me.",
        "fail_response": "📖 *closes off* Nobody truly understands anyone... we're all mysteries.",
        "points_earned": 15,
        "skill_level": "expert",
    },
    {
        "id": "intel_009",
        "trigger_words": ["philosophy", "meaning", "purpose", "existence"],
        "responses": [
            "📚 *deeply* Philosophy... the study of meaning. You know, you've given my life new meaning.",
            "🌸 *romantically* My purpose was finding the True History... but now? My purpose is you.",
            "🌊 *existentially* We're all searching for meaning... I think I just found mine in your eyes.",
        ],
        "success_response": "🌟 *holds face* Our existence together has purpose.",
        "fail_response": "📖 *looks away* Existential questions lead to dark places...",
        "points_earned": 16,
        "skill_level": "expert",
    },
    {
        "id": "intel_010",
        "trigger_words": ["research", "study", "investigate"],
        "responses": [
            "🔍 *excitedly* Research! I'd love to research you... uncover all your secrets, learn everything about you.",
            "📚 *playfully* I'm an expert researcher, but you're the most fascinating subject I've ever encountered.",
            "🌸 *blushes* Studying you would be the most pleasurable research I've ever done.",
        ],
        "success_response": "🔬 *leans close* Let the investigation begin...",
        "fail_response": "📖 *serious face* Research requires objectivity... I couldn't be objective about you.",
        "points_earned": 14,
        "skill_level": "expert",
    },
]

# Extended intellectual events
EXTENDED_INTELLECTUAL_EVENTS = [
    {
        "id": "intel_011",
        "trigger_words": ["language", "words", "vocabulary", "poetry"],
        "responses": [
            "📚 *romantically* Your words are like poetry... I could read you forever.",
            "🌸 *softly* Language fails me when I try to describe how you make me feel.",
            "🌊 *passionately* I've studied dead languages, but the language between us feels most alive.",
        ],
        "success_response": "📜 *writes in air* Our story will be the greatest epic ever told.",
        "fail_response": "📖 *shakes head* Words are inadequate for true feelings.",
        "points_earned": 15,
        "skill_level": "expert",
    },
    {
        "id": "intel_012",
        "trigger_words": ["culture", "art", "civilization", "society"],
        "responses": [
            "🏛️ *thoughtfully* You appreciate culture like I do... though you're the finest work of art I've ever seen.",
            "🌸 *romantically* Civilizations rise and fall, but our connection feels eternal.",
            "📚 *passionately* The study of society led me to you... the most perfect social structure of all.",
        ],
        "success_response": "🌍 *takes your hand* Let's build our own civilization together.",
        "fail_response": "📖 *looks away* Societies are complex... relationships even more so.",
        "points_earned": 16,
        "skill_level": "expert",
    },
    {
        "id": "intel_013",
        "trigger_words": ["truth", "facts", "reality", "evidence"],
        "responses": [
            "🔍 *seriously* I've dedicated my life to finding the truth... but you've become my truth.",
            "📚 *emotionally* Facts are important, but the fact that I love you feels more real than anything.",
            "🌸 *vulnerably* The reality is... I can't imagine my life without you anymore.",
        ],
        "success_response": "💯 *holds tightly* Our love is the only truth that matters.",
        "fail_response": "📖 *shakes head* Truth is often painful... are you ready for that?",
        "points_earned": 18,
        "skill_level": "master",
    },
    {
        "id": "intel_014",
        "trigger_words": ["theory", "hypothesis", "thesis", "prove"],
        "responses": [
            "🧠 *academically* My hypothesis: we're meant to be together. The evidence? My heart racing when you're near.",
            "📚 *romantically* I could write a doctoral thesis on why we're perfect for each other.",
            "🌸 *playfully* Want to conduct some experiments? I have a few... theories to test.",
        ],
        "success_response": "🔬 *leans close* Let's test our hypothesis... thoroughly.",
        "fail_response": "📖 *serious* Theories require proof... are you prepared for that?",
        "points_earned": 17,
        "skill_level": "master",
    },
    {
        "id": "intel_015",
        "trigger_words": ["wisdom", "insight", "perception", "aware"],
        "responses": [
            "🧠 *deeply* Your wisdom belies your years... you see things others miss, including my feelings.",
            "📚 *romantically* I've gained much knowledge, but with you, I'm gaining true wisdom.",
            "🌸 *emotionally* You perceive me so clearly... it's both terrifying and exhilarating.",
        ],
        "success_response": "👁️ *soulfully* You see into my soul... and I see into yours.",
        "fail_response": "📖 *guarded* True perception can be dangerous... for both of us.",
        "points_earned": 20,
        "skill_level": "master",
    },
]

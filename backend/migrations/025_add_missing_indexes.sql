-- Migration 025: fill remaining index gaps for high-traffic lookups.
-- Many of the audit's suggested indexes already exist (quiz_history got its
-- chat + question indexes in 024, filters/notes/swears are covered by their
-- unique hash indexes, warnings and message_history were indexed at creation).
-- These are the genuinely missing ones:

-- Username lookups in plaintext fallback mode (encrypted mode already uses
-- the unique idx_username_cache_hash). Used by every /profile and moderation
-- username resolution while crypto is disabled.
CREATE INDEX IF NOT EXISTS idx_username_cache_username ON username_cache(username);

-- Game-type aggregation (e.g. "all plays of 'quiz' across users"); complements
-- the existing user-first idx_game_stats_user.
CREATE INDEX IF NOT EXISTS idx_game_stats_type ON game_stats(game_type, user_id);

-- Keep planner statistics fresh.
ANALYZE username_cache;
ANALYZE game_stats;

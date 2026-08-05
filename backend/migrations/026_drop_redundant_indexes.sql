-- Migration 026: drop redundant indexes that duplicate the UNIQUE constraint
-- backing indexes created in 023.

-- game_cooldowns has UNIQUE(user_id, game_type); that constraint already backs
-- a unique index with the same (user_id, game_type) column order, which covers
-- all user-first lookups. The explicit non-unique index is pure write overhead.
DROP INDEX IF EXISTS idx_game_cooldowns_user;

-- game_stats has UNIQUE(user_id, game_type); the explicit index is redundant
-- with the constraint backing index. The complementary game_type-first index
-- (idx_game_stats_type, from 025) is retained for type aggregation.
DROP INDEX IF EXISTS idx_game_stats_user;

INSERT INTO _migrations (name) VALUES ('026_drop_redundant_indexes')
ON CONFLICT (name) DO NOTHING;
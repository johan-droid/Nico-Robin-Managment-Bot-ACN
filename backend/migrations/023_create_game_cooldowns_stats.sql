-- Per-user per-game-instance cooldown tracking.
-- NOTE: user_id is a bare BIGINT (no FK) to match every other table in this schema.
CREATE TABLE IF NOT EXISTS game_cooldowns (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL, -- 'voyage', 'quiz', 'bounty_claim', 'crew_voyage'
    last_played_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cooldown_seconds INT NOT NULL DEFAULT 600, -- Game-specific cooldown duration
    UNIQUE(user_id, game_type)
);

CREATE INDEX IF NOT EXISTS idx_game_cooldowns_user ON game_cooldowns(user_id, game_type);

-- Per-user game-level metrics (plays / wins).
CREATE TABLE IF NOT EXISTS game_stats (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    wins INT NOT NULL DEFAULT 0,
    plays INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, game_type)
);

CREATE INDEX IF NOT EXISTS idx_game_stats_user ON game_stats(user_id, game_type);

-- Crew-level aggregate metrics.
CREATE TABLE IF NOT EXISTS crew_stats (
    id SERIAL PRIMARY KEY,
    crew_id INTEGER NOT NULL UNIQUE REFERENCES pirate_crews(id) ON DELETE CASCADE,
    total_bounty_earned BIGINT NOT NULL DEFAULT 0,
    avg_member_bounty BIGINT NOT NULL DEFAULT 0,
    total_crew_voyages INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Command execution history for anti-spam throttling + moderation audit.
CREATE TABLE IF NOT EXISTS command_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    command VARCHAR(100) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success BOOLEAN,
    error_msg VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_command_history_user_time ON command_history(user_id, command, executed_at);

CREATE TABLE IF NOT EXISTS economy_profiles (
    user_id BIGINT NOT NULL PRIMARY KEY,
    coins BIGINT NOT NULL DEFAULT 0,
    xp BIGINT NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    reputation INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS xp_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES economy_profiles(user_id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_rewards (
    user_id BIGINT NOT NULL PRIMARY KEY REFERENCES economy_profiles(user_id) ON DELETE CASCADE,
    last_claimed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    streak INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS leaderboards (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    score BIGINT NOT NULL DEFAULT 0,
    rank_type VARCHAR(50) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id, rank_type)
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    game_type VARCHAR(50) NOT NULL,
    state JSONB NOT NULL DEFAULT '{}',
    started_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    options JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS one_piece_bounties (
    user_id BIGINT NOT NULL PRIMARY KEY,
    bounty BIGINT NOT NULL DEFAULT 0,
    title VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_pairings (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user1_id BIGINT NOT NULL,
    user2_id BIGINT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (group_id, date)
);

CREATE TABLE IF NOT EXISTS log_channels (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    log_types JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS ai_settings (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    model VARCHAR(50) NOT NULL DEFAULT 'gpt-4',
    temperature FLOAT NOT NULL DEFAULT 0.7
);

CREATE TABLE IF NOT EXISTS ai_memory (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_memory_group ON ai_memory(group_id);

CREATE TABLE IF NOT EXISTS prompt_overrides (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE PRIMARY KEY,
    system_prompt TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_cooldowns (
    user_id BIGINT NOT NULL PRIMARY KEY,
    last_request TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_count INTEGER NOT NULL DEFAULT 1
);

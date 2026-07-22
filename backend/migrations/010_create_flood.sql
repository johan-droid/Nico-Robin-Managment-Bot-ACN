CREATE TABLE IF NOT EXISTS flood_settings (
    group_id BIGINT PRIMARY KEY REFERENCES groups(chat_id) ON DELETE CASCADE,
    flood_limit INTEGER NOT NULL DEFAULT 5,
    flood_mode VARCHAR(50) NOT NULL DEFAULT 'warn',
    flood_window_seconds INTEGER NOT NULL DEFAULT 10,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

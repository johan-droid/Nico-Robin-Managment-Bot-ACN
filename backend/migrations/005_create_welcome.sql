CREATE TABLE IF NOT EXISTS welcome_settings (
    group_id BIGINT PRIMARY KEY REFERENCES groups(chat_id) ON DELETE CASCADE,
    welcome_message TEXT,
    farewell_message TEXT,
    welcome_dm_message TEXT,
    clean_welcome BOOLEAN NOT NULL DEFAULT FALSE,
    captcha_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

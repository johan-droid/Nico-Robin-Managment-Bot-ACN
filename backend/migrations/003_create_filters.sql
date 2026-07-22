CREATE TABLE IF NOT EXISTS filters (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    trigger_text VARCHAR(500) NOT NULL,
    response TEXT NOT NULL,
    action_type VARCHAR(50) NOT NULL DEFAULT 'reply',
    created_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(group_id, trigger_text)
);

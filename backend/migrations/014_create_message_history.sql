CREATE TABLE IF NOT EXISTS message_history (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    user_name TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    date BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chat_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_message_history_chat_id ON message_history (chat_id);
CREATE INDEX IF NOT EXISTS idx_message_history_chat_date ON message_history (chat_id, date DESC);

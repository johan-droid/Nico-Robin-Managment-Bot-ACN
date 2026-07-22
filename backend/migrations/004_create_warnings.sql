CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    warned_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_warnings_group_user ON warnings(group_id, user_id);

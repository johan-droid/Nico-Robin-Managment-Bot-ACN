CREATE TABLE IF NOT EXISTS feature_flags (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    toggled_by BIGINT NOT NULL,
    toggled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(group_id, feature_name)
);

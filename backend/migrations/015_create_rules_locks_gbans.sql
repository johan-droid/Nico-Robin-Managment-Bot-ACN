CREATE TABLE IF NOT EXISTS group_rules (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    rules TEXT NOT NULL DEFAULT '',
    updated_by BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id)
);

CREATE TABLE IF NOT EXISTS group_locks (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    lock_type VARCHAR(50) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    toggled_by BIGINT NOT NULL DEFAULT 0,
    toggled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, lock_type)
);

CREATE TABLE IF NOT EXISTS gbans (
    user_id BIGINT NOT NULL PRIMARY KEY,
    user_name TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT 'No reason provided',
    banned_by BIGINT NOT NULL DEFAULT 0,
    banned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

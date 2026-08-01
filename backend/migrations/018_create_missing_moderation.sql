CREATE TABLE IF NOT EXISTS mutes (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    muted_by BIGINT NOT NULL,
    muted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS temp_mutes (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    muted_by BIGINT NOT NULL,
    muted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_temp_mutes_expires ON temp_mutes(expires_at);

CREATE TABLE IF NOT EXISTS temp_bans (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    banned_by BIGINT NOT NULL,
    banned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_temp_bans_expires ON temp_bans(expires_at);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    target_id BIGINT,
    executor_id BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_group ON audit_logs(group_id);

CREATE TABLE IF NOT EXISTS admin_cache (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS trusted_users (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS blacklisted_users (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    reason TEXT,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS whitelists (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id)
);

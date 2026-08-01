CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_by BIGINT NOT NULL,
    run_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_run_at ON scheduled_jobs(run_at);

CREATE TABLE IF NOT EXISTS auto_deletes (
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    delay_seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (group_id, message_type)
);

CREATE TABLE IF NOT EXISTS timers (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    interval_seconds INTEGER NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    remind_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at);

CREATE TABLE IF NOT EXISTS backup_jobs (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
    backup_url TEXT NOT NULL,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

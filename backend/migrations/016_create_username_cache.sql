-- Migration 016: username_cache table
-- Previously created inline in src/main.rs on every boot; moved here so all
-- schema DDL is owned by the migration system (applied by the `migrate` binary).
CREATE TABLE IF NOT EXISTS username_cache (
    username TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    first_name TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_username_cache_user_id ON username_cache(user_id);

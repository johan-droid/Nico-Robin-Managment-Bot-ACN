-- Migration 012: Encrypt sensitive data at rest
--
-- All TEXT/VARCHAR columns that may contain user data, group context,
-- or bot configuration are encrypted with AES-256-GCM at the
-- application layer (Rust crypto module) before being stored.
--
-- Lookup columns that require matching (swear_words.word) get a
-- companion hash column so the application can do efficient lookups
-- without exposing the plaintext.

-- Add hash column for swear_words.word lookups and dedup
ALTER TABLE swear_words ADD COLUMN IF NOT EXISTS word_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_swear_words_group_word_hash
    ON swear_words(group_id, word_hash) WHERE word_hash IS NOT NULL;

-- Track this migration
CREATE TABLE IF NOT EXISTS _migrations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO _migrations (name) VALUES ('012_encrypt_sensitive_data')
ON CONFLICT (name) DO NOTHING;

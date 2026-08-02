-- Migration 021: Encrypt remaining text fields

-- notes
ALTER TABLE notes ADD COLUMN IF NOT EXISTS name_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_group_name_hash
    ON notes(group_id, name_hash) WHERE name_hash IS NOT NULL;

-- filters
ALTER TABLE filters ADD COLUMN IF NOT EXISTS trigger_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_filters_group_trigger_hash
    ON filters(group_id, trigger_hash) WHERE trigger_hash IS NOT NULL;

-- username_cache
-- We drop the existing PK on `username` because it will be encrypted (and thus randomized).
-- We add an auto-incrementing `id` as the new PK, and an indexed `username_hash` for fast lookups.
ALTER TABLE username_cache DROP CONSTRAINT IF EXISTS username_cache_pkey CASCADE;
ALTER TABLE username_cache ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;
ALTER TABLE username_cache ADD COLUMN IF NOT EXISTS username_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_username_cache_hash 
    ON username_cache(username_hash) WHERE username_hash IS NOT NULL;

-- Track this migration
INSERT INTO _migrations (name) VALUES ('021_encrypt_remaining_text')
ON CONFLICT (name) DO NOTHING;

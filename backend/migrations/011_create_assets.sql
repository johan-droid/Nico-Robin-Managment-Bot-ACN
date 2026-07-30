CREATE TABLE IF NOT EXISTS bot_assets (
    key TEXT PRIMARY KEY,
    data BYTEA NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'image/jpeg',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

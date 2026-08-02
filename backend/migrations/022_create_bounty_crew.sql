CREATE TABLE IF NOT EXISTS pirate_crews (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    captain_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pirate_crew_members (
    crew_id INTEGER NOT NULL REFERENCES pirate_crews(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL PRIMARY KEY,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pirate_crew_invites (
    crew_id INTEGER NOT NULL REFERENCES pirate_crews(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    invited_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (crew_id, user_id)
);

ALTER TABLE one_piece_bounties ADD COLUMN IF NOT EXISTS last_daily_checkin TIMESTAMPTZ;
ALTER TABLE one_piece_bounties ADD COLUMN IF NOT EXISTS last_voyage TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS federations (
    fed_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    creator_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS federation_groups (
    fed_id VARCHAR(50) NOT NULL REFERENCES federations(fed_id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL,
    PRIMARY KEY (fed_id, group_id)
);

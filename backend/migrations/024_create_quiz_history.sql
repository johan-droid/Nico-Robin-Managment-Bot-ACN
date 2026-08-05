-- Persistent quiz history per chat, so questions don't repeat across restarts.
CREATE TABLE IF NOT EXISTS quiz_history (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    question_id INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    user_id BIGINT,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    was_correct BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_chat_recent ON quiz_history(chat_id, answered_at DESC);
CREATE INDEX IF NOT EXISTS idx_question_usage ON quiz_history(question_id, answered_at DESC);

-- Question usage tracking for weighted random selection.
ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

-- Per-user quiz performance (bare BIGINT user_id, matching every other table).
CREATE TABLE IF NOT EXISTS user_quiz_stats (
    user_id BIGINT NOT NULL PRIMARY KEY,
    total_attempts INTEGER NOT NULL DEFAULT 0,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    wrong_answers INTEGER NOT NULL DEFAULT 0,
    last_quiz_at TIMESTAMPTZ
);

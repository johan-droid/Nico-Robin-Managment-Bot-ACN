use tokio_postgres::Client;

#[derive(Debug, Clone)]
pub struct UserQuizStats {
    pub total_attempts: i32,
    pub correct_answers: i32,
    pub wrong_answers: i32,
    pub accuracy: f64,
}

/// Records a quiz attempt for persistent tracking: writes the history row,
/// bumps per-user stats, and increments the question's usage counter.
pub async fn record_quiz_attempt(
    client: &Client,
    chat_id: i64,
    question_id: i32,
    user_id: i64,
    was_correct: bool,
) -> Result<(), String> {
    let stmt = client
        .prepare(
            "INSERT INTO quiz_history (chat_id, question_id, user_id, was_correct, answered_at)
             VALUES ($1, $2, $3, $4, NOW())",
        )
        .await
        .map_err(|e| e.to_string())?;
    client
        .execute(&stmt, &[&chat_id, &question_id, &user_id, &was_correct])
        .await
        .map_err(|e| e.to_string())?;

    let correct: i32 = if was_correct { 1 } else { 0 };
    let wrong: i32 = if was_correct { 0 } else { 1 };
    let stats_stmt = client
        .prepare(
            "INSERT INTO user_quiz_stats (user_id, total_attempts, correct_answers, wrong_answers, last_quiz_at)
             VALUES ($1, 1, $2, $3, NOW())
             ON CONFLICT (user_id)
             DO UPDATE SET
                 total_attempts = user_quiz_stats.total_attempts + 1,
                 correct_answers = user_quiz_stats.correct_answers + EXCLUDED.correct_answers,
                 wrong_answers = user_quiz_stats.wrong_answers + EXCLUDED.wrong_answers,
                 last_quiz_at = NOW()",
        )
        .await
        .map_err(|e| e.to_string())?;
    client
        .execute(&stats_stmt, &[&user_id, &correct, &wrong])
        .await
        .map_err(|e| e.to_string())?;

    let usage_stmt = client
        .prepare(
            "UPDATE quiz_questions SET usage_count = usage_count + 1, last_used_at = NOW()
             WHERE id = $1",
        )
        .await
        .map_err(|e| e.to_string())?;
    client
        .execute(&usage_stmt, &[&question_id])
        .await
        .map_err(|e| e.to_string())?;

    Ok(())
}

/// Question IDs recently asked in this chat, most recent first.
pub async fn get_recent_question_ids_db(
    client: &Client,
    chat_id: i64,
    limit: i32,
) -> Result<Vec<i32>, String> {
    let stmt = client
        .prepare(
            "SELECT question_id FROM (
                SELECT question_id, MAX(answered_at) AS last_asked
                FROM quiz_history
                WHERE chat_id = $1
                GROUP BY question_id
                ORDER BY last_asked DESC
                LIMIT $2
             ) recent",
        )
        .await
        .map_err(|e| e.to_string())?;

    let rows = client
        .query(&stmt, &[&chat_id, &limit])
        .await
        .map_err(|e| e.to_string())?;

    Ok(rows.iter().map(|row| row.get(0)).collect())
}

/// Picks a question weighted away from recently used and over-used ones:
/// excludes the last `excluded` ids, prefers least-used questions, and
/// lets questions rest 30 minutes between appearances.
pub async fn get_random_quiz_smart(
    client: &Client,
    exclude_ids: &[i32],
) -> Result<Option<(i32, String, String, Vec<String>)>, String> {
    let stmt = client
        .prepare(
            "SELECT id, question, answer, options
             FROM quiz_questions
             WHERE category = 'one_piece'
               AND NOT (id = ANY($1))
               AND (last_used_at IS NULL OR
                    EXTRACT(EPOCH FROM (NOW() - last_used_at)) > 1800)
             ORDER BY usage_count ASC, RANDOM()
             LIMIT 1",
        )
        .await
        .map_err(|e| e.to_string())?;

    let row_opt = client
        .query_opt(&stmt, &[&exclude_ids])
        .await
        .map_err(|e| e.to_string())?;

    let Some(row) = row_opt else {
        return Ok(None);
    };

    let id: i32 = row.get(0);
    let question: String = row.get(1);
    let answer: String = row.get(2);

    let options: serde_json::Value = match row.try_get(3) {
        Ok(v) => v,
        Err(e) => {
            tracing::error!("Failed to get options for question {}: {}", id, e);
            serde_json::Value::Null
        }
    };

    let options: Vec<String> = serde_json::from_value(options).unwrap_or_else(|e| {
        tracing::warn!("Failed to parse options JSON for question {}: {}", id, e);
        vec![]
    });

    Ok(Some((id, question, answer, options)))
}

/// Per-user quiz performance for `/quizstats`.
pub async fn get_user_quiz_stats(
    client: &Client,
    user_id: i64,
) -> Result<Option<UserQuizStats>, String> {
    let stmt = client
        .prepare(
            "SELECT total_attempts, correct_answers, wrong_answers,
                    ROUND(100.0 * correct_answers / NULLIF(total_attempts, 0), 1)::FLOAT8 AS accuracy
             FROM user_quiz_stats WHERE user_id = $1",
        )
        .await
        .map_err(|e| e.to_string())?;

    let row_opt = client
        .query_opt(&stmt, &[&user_id])
        .await
        .map_err(|e| e.to_string())?;

    let Some(row) = row_opt else {
        return Ok(None);
    };

    Ok(Some(UserQuizStats {
        total_attempts: row.get(0),
        correct_answers: row.get(1),
        wrong_answers: row.get(2),
        accuracy: row.get::<_, f64>(3),
    }))
}

/// Top quiz performers as `(rank, user_id, correct_answers, total_attempts, accuracy)`.
pub async fn get_quiz_leaderboard(
    client: &Client,
    limit: i64,
) -> Result<Vec<(i32, i64, i32, i32, f64)>, String> {
    let stmt = client
        .prepare(
            "SELECT
                ROW_NUMBER() OVER (ORDER BY correct_answers DESC, total_attempts ASC, user_id ASC)::INT AS rank,
                user_id,
                correct_answers,
                total_attempts,
                ROUND(100.0 * correct_answers / NULLIF(total_attempts, 0), 1)::FLOAT8 AS accuracy
             FROM user_quiz_stats
             WHERE total_attempts > 0
             ORDER BY correct_answers DESC, total_attempts ASC, user_id ASC
             LIMIT $1",
        )
        .await
        .map_err(|e| e.to_string())?;

    let rows = client
        .query(&stmt, &[&limit])
        .await
        .map_err(|e| e.to_string())?;

    let mut lb = Vec::new();
    for row in rows {
        lb.push((row.get(0), row.get(1), row.get(2), row.get(3), row.get(4)));
    }
    Ok(lb)
}

/// Quiz pool summary as `(total_questions, questions_used_at_least_once)`.
pub async fn quiz_pool_stats(client: &Client) -> Result<(i64, i64), String> {
    let stmt = client
        .prepare(
            "SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE usage_count > 0) AS used
             FROM quiz_questions WHERE category = 'one_piece'",
        )
        .await
        .map_err(|e| e.to_string())?;

    let row = client
        .query_one(&stmt, &[])
        .await
        .map_err(|e| e.to_string())?;

    Ok((row.get(0), row.get(1)))
}

/// Resets a question's usage counter. Returns false if the id does not exist.
pub async fn reset_question_usage(client: &Client, question_id: i32) -> Result<bool, String> {
    let stmt = client
        .prepare("UPDATE quiz_questions SET usage_count = 0, last_used_at = NULL WHERE id = $1")
        .await
        .map_err(|e| e.to_string())?;
    let updated = client
        .execute(&stmt, &[&question_id])
        .await
        .map_err(|e| e.to_string())?;
    Ok(updated > 0)
}

/// Deletes a question from the pool. Returns false if the id does not exist.
pub async fn remove_question(client: &Client, question_id: i32) -> Result<bool, String> {
    let stmt = client
        .prepare("DELETE FROM quiz_questions WHERE id = $1")
        .await
        .map_err(|e| e.to_string())?;
    let deleted = client
        .execute(&stmt, &[&question_id])
        .await
        .map_err(|e| e.to_string())?;
    Ok(deleted > 0)
}

use sqlx::PgPool;

/// Adds a warning for a user in a group.
pub async fn add_warning(
    pool: &PgPool,
    group_id: i64,
    user_id: i64,
    reason: &str,
    warned_by: i64,
) -> Result<i32, sqlx::Error> {
    let row: (i32,) = sqlx::query_as(
        r#"INSERT INTO warnings (group_id, user_id, reason, warned_by)
           VALUES ($1, $2, $3, $4) RETURNING id"#,
    )
    .bind(group_id)
    .bind(user_id)
    .bind(reason)
    .bind(warned_by)
    .fetch_one(pool)
    .await?;
    Ok(row.0)
}

/// Gets the warning count for a user in a group.
pub async fn get_warning_count(
    pool: &PgPool,
    group_id: i64,
    user_id: i64,
) -> Result<i64, sqlx::Error> {
    let row: (i64,) =
        sqlx::query_as(r#"SELECT COUNT(*) FROM warnings WHERE group_id = $1 AND user_id = $2"#)
            .bind(group_id)
            .bind(user_id)
            .fetch_one(pool)
            .await?;
    Ok(row.0)
}

/// Gets all warnings for a user in a group.
pub async fn get_warnings(
    pool: &PgPool,
    group_id: i64,
    user_id: i64,
) -> Result<Vec<(i32, String, i64)>, sqlx::Error> {
    let rows: Vec<(i32, String, i64)> = sqlx::query_as(
        r#"SELECT id, reason, warned_by FROM warnings
           WHERE group_id = $1 AND user_id = $2 ORDER BY created_at"#,
    )
    .bind(group_id)
    .bind(user_id)
    .fetch_all(pool)
    .await?;
    Ok(rows)
}

/// Resets all warnings for a user in a group.
pub async fn reset_warnings(
    pool: &PgPool,
    group_id: i64,
    user_id: i64,
) -> Result<u64, sqlx::Error> {
    let result = sqlx::query(r#"DELETE FROM warnings WHERE group_id = $1 AND user_id = $2"#)
        .bind(group_id)
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(result.rows_affected())
}

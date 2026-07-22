use sqlx::PgPool;

pub async fn add_swear(pool: &PgPool, group_id: i64, word: &str) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO swear_words (group_id, word) VALUES ($1, $2)
           ON CONFLICT (group_id, word) DO NOTHING"#,
    )
    .bind(group_id)
    .bind(word.to_lowercase())
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn remove_swear(pool: &PgPool, group_id: i64, word: &str) -> Result<bool, sqlx::Error> {
    let result = sqlx::query(
        r#"DELETE FROM swear_words WHERE group_id = $1 AND word = $2"#,
    )
    .bind(group_id)
    .bind(word.to_lowercase())
    .execute(pool)
    .await?;
    Ok(result.rows_affected() > 0)
}

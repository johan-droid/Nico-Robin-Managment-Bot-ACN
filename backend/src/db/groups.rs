use sqlx::PgPool;

/// Ensures a group exists in the database, inserting if necessary.
pub async fn ensure_group(pool: &PgPool, chat_id: i64, title: &str) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO groups (chat_id, title) VALUES ($1, $2)
           ON CONFLICT (chat_id) DO UPDATE SET title = $2, updated_at = NOW()"#,
    )
    .bind(chat_id)
    .bind(title)
    .execute(pool)
    .await?;
    Ok(())
}

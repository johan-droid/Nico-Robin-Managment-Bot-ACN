use sqlx::PgPool;

/// Saves a note for a group.
pub async fn save_note(
    pool: &PgPool,
    group_id: i64,
    name: &str,
    content: &str,
    created_by: i64,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO notes (group_id, name, content, created_by)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id, name) DO UPDATE SET content = $3"#,
    )
    .bind(group_id)
    .bind(name)
    .bind(content)
    .bind(created_by)
    .execute(pool)
    .await?;
    Ok(())
}

/// Gets a note by name for a group.
pub async fn get_note(pool: &PgPool, group_id: i64, name: &str) -> Result<Option<String>, sqlx::Error> {
    let row: Option<(String,)> = sqlx::query_as(
        r#"SELECT content FROM notes WHERE group_id = $1 AND name = $2"#,
    )
    .bind(group_id)
    .bind(name)
    .fetch_optional(pool)
    .await?;
    Ok(row.map(|r| r.0))
}

/// Lists all notes for a group.
pub async fn list_notes(pool: &PgPool, group_id: i64) -> Result<Vec<String>, sqlx::Error> {
    let rows: Vec<(String,)> = sqlx::query_as(
        r#"SELECT name FROM notes WHERE group_id = $1 ORDER BY name"#,
    )
    .bind(group_id)
    .fetch_all(pool)
    .await?;
    Ok(rows.into_iter().map(|r| r.0).collect())
}

/// Deletes a note by name for a group.
pub async fn delete_note(pool: &PgPool, group_id: i64, name: &str) -> Result<bool, sqlx::Error> {
    let result = sqlx::query(
        r#"DELETE FROM notes WHERE group_id = $1 AND name = $2"#,
    )
    .bind(group_id)
    .bind(name)
    .execute(pool)
    .await?;
    Ok(result.rows_affected() > 0)
}

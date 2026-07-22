use sqlx::PgPool;

/// Creates a new federation.
pub async fn create_federation(
    pool: &PgPool,
    fed_id: &str,
    name: &str,
    creator_id: i64,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO federations (fed_id, name, creator_id) VALUES ($1, $2, $3)"#,
    )
    .bind(fed_id)
    .bind(name)
    .bind(creator_id)
    .execute(pool)
    .await?;
    Ok(())
}

/// Joins a group to a federation.
pub async fn join_federation(pool: &PgPool, fed_id: &str, group_id: i64) -> Result<bool, sqlx::Error> {
    let result = sqlx::query(
        r#"INSERT INTO federation_groups (fed_id, group_id) VALUES ($1, $2)
           ON CONFLICT DO NOTHING"#,
    )
    .bind(fed_id)
    .bind(group_id)
    .execute(pool)
    .await?;
    Ok(result.rows_affected() > 0)
}

/// Checks if a federation exists.
pub async fn federation_exists(pool: &PgPool, fed_id: &str) -> Result<bool, sqlx::Error> {
    let row: Option<(String,)> = sqlx::query_as(
        r#"SELECT fed_id FROM federations WHERE fed_id = $1"#,
    )
    .bind(fed_id)
    .fetch_optional(pool)
    .await?;
    Ok(row.is_some())
}

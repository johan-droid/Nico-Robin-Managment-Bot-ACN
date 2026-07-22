use sqlx::PgPool;

pub async fn get_flood_settings(
    pool: &PgPool,
    group_id: i64,
) -> Result<Option<(i32, String, i32)>, sqlx::Error> {
    let row: Option<(i32, String, i32)> = sqlx::query_as(
        r#"SELECT flood_limit, flood_mode, flood_window_seconds
           FROM flood_settings WHERE group_id = $1"#,
    )
    .bind(group_id)
    .fetch_optional(pool)
    .await?;
    Ok(row)
}

pub async fn set_flood_settings(
    pool: &PgPool,
    group_id: i64,
    limit: i32,
    mode: &str,
    window: i32,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO flood_settings (group_id, flood_limit, flood_mode, flood_window_seconds)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id) DO UPDATE SET flood_limit = $2, flood_mode = $3,
           flood_window_seconds = $4, updated_at = NOW()"#,
    )
    .bind(group_id)
    .bind(limit)
    .bind(mode)
    .bind(window)
    .execute(pool)
    .await?;
    Ok(())
}

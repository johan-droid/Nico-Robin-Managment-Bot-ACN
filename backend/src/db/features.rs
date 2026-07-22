use sqlx::PgPool;

/// Checks if a feature is enabled for a group.
pub async fn is_feature_enabled(
    pool: &PgPool,
    group_id: i64,
    feature_name: &str,
) -> Result<bool, sqlx::Error> {
    let row: Option<(bool,)> = sqlx::query_as(
        r#"SELECT enabled FROM feature_flags WHERE group_id = $1 AND feature_name = $2"#,
    )
    .bind(group_id)
    .bind(feature_name)
    .fetch_optional(pool)
    .await?;
    Ok(row.map(|r| r.0).unwrap_or(true))
}

/// Enables a feature for a group.
pub async fn enable_feature(
    pool: &PgPool,
    group_id: i64,
    feature_name: &str,
    toggled_by: i64,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO feature_flags (group_id, feature_name, enabled, toggled_by)
           VALUES ($1, $2, TRUE, $3)
           ON CONFLICT (group_id, feature_name) DO UPDATE SET enabled = TRUE, toggled_by = $3, toggled_at = NOW()"#,
    )
    .bind(group_id)
    .bind(feature_name)
    .bind(toggled_by)
    .execute(pool)
    .await?;
    Ok(())
}

/// Disables a feature for a group.
pub async fn disable_feature(
    pool: &PgPool,
    group_id: i64,
    feature_name: &str,
    toggled_by: i64,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO feature_flags (group_id, feature_name, enabled, toggled_by)
           VALUES ($1, $2, FALSE, $3)
           ON CONFLICT (group_id, feature_name) DO UPDATE SET enabled = FALSE, toggled_by = $3, toggled_at = NOW()"#,
    )
    .bind(group_id)
    .bind(feature_name)
    .bind(toggled_by)
    .execute(pool)
    .await?;
    Ok(())
}

/// Lists all features and their status for a group.
pub async fn list_features(
    pool: &PgPool,
    group_id: i64,
) -> Result<Vec<(String, bool)>, sqlx::Error> {
    let rows: Vec<(String, bool)> = sqlx::query_as(
        r#"SELECT feature_name, enabled FROM feature_flags WHERE group_id = $1 ORDER BY feature_name"#,
    )
    .bind(group_id)
    .fetch_all(pool)
    .await?;
    Ok(rows)
}

/// Resets all feature flags for a group (back to defaults).
pub async fn reset_features(pool: &PgPool, group_id: i64) -> Result<u64, sqlx::Error> {
    let result = sqlx::query(r#"DELETE FROM feature_flags WHERE group_id = $1"#)
        .bind(group_id)
        .execute(pool)
        .await?;
    Ok(result.rows_affected())
}

use tokio_postgres::Client;

/// Checks if a feature is enabled for a group.
pub async fn is_feature_enabled(
    client: &Client,
    group_id: i64,
    feature_name: &str,
) -> Result<bool, String> {
    let row = client.query_opt(
        r#"SELECT enabled FROM feature_flags WHERE group_id = $1 AND feature_name = $2"#,
        &[&group_id, &feature_name]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(row.map(|r| r.get::<usize, bool>(0)).unwrap_or(true))
}

/// Enables a feature for a group.
pub async fn enable_feature(
    client: &Client,
    group_id: i64,
    feature_name: &str,
    toggled_by: i64,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO feature_flags (group_id, feature_name, enabled, toggled_by)
           VALUES ($1, $2, TRUE, $3)
           ON CONFLICT (group_id, feature_name) DO UPDATE SET enabled = TRUE, toggled_by = $3, toggled_at = NOW()"#,
        &[&group_id, &feature_name, &toggled_by]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Disables a feature for a group.
pub async fn disable_feature(
    client: &Client,
    group_id: i64,
    feature_name: &str,
    toggled_by: i64,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO feature_flags (group_id, feature_name, enabled, toggled_by)
           VALUES ($1, $2, FALSE, $3)
           ON CONFLICT (group_id, feature_name) DO UPDATE SET enabled = FALSE, toggled_by = $3, toggled_at = NOW()"#,
        &[&group_id, &feature_name, &toggled_by]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Lists all features and their status for a group.
pub async fn list_features(
    client: &Client,
    group_id: i64,
) -> Result<Vec<(String, bool)>, String> {
    let rows = client.query(
        r#"SELECT feature_name, enabled FROM feature_flags WHERE group_id = $1 ORDER BY feature_name"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(rows.into_iter().map(|row| (row.get(0), row.get(1))).collect())
}

/// Resets all feature flags for a group (back to defaults).
pub async fn reset_features(client: &Client, group_id: i64) -> Result<u64, String> {
    let result = client.execute(
        r#"DELETE FROM feature_flags WHERE group_id = $1"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(result)
}

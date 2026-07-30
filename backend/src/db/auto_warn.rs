use tokio_postgres::Client;

pub async fn is_auto_warn_enabled(client: &Client, group_id: i64) -> Result<bool, String> {
    let row = client
        .query_opt(
            "SELECT enabled FROM auto_warn_settings WHERE group_id = $1",
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.map(|r| r.get::<usize, bool>(0)).unwrap_or(true))
}

pub async fn enable_auto_warn(client: &Client, group_id: i64) -> Result<(), String> {
    client
        .execute(
            "INSERT INTO auto_warn_settings (group_id, enabled) VALUES ($1, TRUE) ON CONFLICT (group_id) DO UPDATE SET enabled = TRUE, updated_at = NOW()",
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn disable_auto_warn(client: &Client, group_id: i64) -> Result<(), String> {
    client
        .execute(
            "INSERT INTO auto_warn_settings (group_id, enabled) VALUES ($1, FALSE) ON CONFLICT (group_id) DO UPDATE SET enabled = FALSE, updated_at = NOW()",
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

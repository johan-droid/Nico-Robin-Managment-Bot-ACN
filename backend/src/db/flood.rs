use tokio_postgres::Client;

pub async fn get_flood_settings(
    client: &Client,
    group_id: i64,
) -> Result<Option<(i32, String, i32)>, String> {
    let row = client
        .query_opt(
            r#"SELECT flood_limit, flood_mode, flood_window_seconds
           FROM flood_settings WHERE group_id = $1"#,
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(row.map(|r| (r.get(0), r.get(1), r.get(2))))
}

pub async fn set_flood_settings(
    client: &Client,
    group_id: i64,
    limit: i32,
    mode: &str,
    window: i32,
) -> Result<(), String> {
    client
        .execute(
            r#"INSERT INTO flood_settings (group_id, flood_limit, flood_mode, flood_window_seconds)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id) DO UPDATE SET flood_limit = $2, flood_mode = $3,
           flood_window_seconds = $4, updated_at = NOW()"#,
            &[&group_id, &limit, &mode, &window],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

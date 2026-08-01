use tokio_postgres::Client;

pub async fn set_admin_cache(
    client: &Client,
    group_id: i64,
    user_id: i64,
    status: &str,
) -> Result<(), String> {
    client.execute(
        "INSERT INTO admin_cache (group_id, user_id, status) VALUES ($1, $2, $3) ON CONFLICT (group_id, user_id) DO UPDATE SET status = $3, updated_at = NOW()",
        &[&group_id, &user_id, &status],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

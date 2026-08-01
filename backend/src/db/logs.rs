use tokio_postgres::Client;

pub async fn log_action(client: &Client, group_id: i64, action: &str, target_id: Option<i64>, executor_id: i64, reason: Option<&str>) -> Result<(), String> {
    client.execute(
        "INSERT INTO audit_logs (group_id, action, target_id, executor_id, reason) VALUES ($1, $2, $3, $4, $5)",
        &[&group_id, &action, &target_id, &executor_id, &reason],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

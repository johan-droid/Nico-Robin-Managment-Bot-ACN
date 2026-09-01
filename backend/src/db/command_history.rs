use tokio_postgres::Client;

/// Records a command execution in `command_history` for audit + throttling.
/// Errors are swallowed by design — logging must never block the command path.
pub async fn log_command(
    client: &Client,
    user_id: i64,
    command: &str,
    success: Option<bool>,
    error_msg: Option<&str>,
) {
    if !crate::config::Settings::global().enable_command_logging {
        return;
    }
    let stmt = match client
        .prepare(
            "INSERT INTO command_history (user_id, command, success, error_msg)
             VALUES ($1, $2, $3, $4)",
        )
        .await
    {
        Ok(s) => s,
        Err(_) => return,
    };
    let _ = client
        .execute(&stmt, &[&user_id, &command, &success, &error_msg])
        .await;
}

/// Checks whether the user has room under `max_per_minute` invocations of the
/// given command in the last minute. Returns `Ok(true)` when allowed.
pub async fn check_command_rate_limit(
    client: &Client,
    user_id: i64,
    command: &str,
    max_per_minute: i32,
) -> Result<bool, String> {
    let stmt = client
        .prepare(
            "SELECT COUNT(*) FROM command_history
             WHERE user_id = $1 AND command = $2
             AND executed_at > NOW() - INTERVAL '1 minute'",
        )
        .await
        .map_err(|e| e.to_string())?;

    let row = client
        .query_one(&stmt, &[&user_id, &command])
        .await
        .map_err(|e| e.to_string())?;

    let count: i64 = row.get(0);
    Ok(count < max_per_minute as i64)
}

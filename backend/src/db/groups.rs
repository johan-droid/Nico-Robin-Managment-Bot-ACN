use tokio_postgres::Client;

/// Ensures a group exists in the database, inserting if necessary.
#[allow(dead_code)]
pub async fn ensure_group(client: &Client, chat_id: i64, title: &str) -> Result<(), String> {
    client
        .execute(
            r#"INSERT INTO groups (chat_id, title) VALUES ($1, $2)
           ON CONFLICT (chat_id) DO UPDATE SET title = $2, updated_at = NOW()"#,
            &[&chat_id, &title],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

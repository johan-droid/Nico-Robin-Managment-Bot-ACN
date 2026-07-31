use tokio_postgres::Client;

/// Ensures a group exists in the database, inserting if necessary.
#[allow(dead_code)]
pub async fn ensure_group(client: &Client, chat_id: i64, title: &str) -> Result<(), String> {
    let title_enc = crate::crypto::try_encrypt(title);
    client
        .execute(
            r#"INSERT INTO groups (chat_id, title) VALUES ($1, $2)
           ON CONFLICT (chat_id) DO UPDATE SET title = $2, updated_at = NOW()"#,
            &[&chat_id, &title_enc],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Returns all known group chat ids (used for global bans).
pub async fn list_groups(client: &Client) -> Result<Vec<i64>, String> {
    let rows = client
        .query("SELECT chat_id FROM groups ORDER BY chat_id", &[])
        .await
        .map_err(|e| e.to_string())?;
    Ok(rows.into_iter().map(|r| r.get(0)).collect())
}

use tokio_postgres::Client;

pub async fn get_asset(client: &Client, key: &str) -> Result<Option<(Vec<u8>, String)>, String> {
    let rows = client
        .query("SELECT data, mime_type FROM bot_assets WHERE key = $1", &[&key])
        .await
        .map_err(|e| e.to_string())?;

    if let Some(row) = rows.into_iter().next() {
        let data: Vec<u8> = row.get(0);
        let mime_type: String = row.get(1);
        Ok(Some((data, mime_type)))
    } else {
        Ok(None)
    }
}

pub async fn set_asset(client: &Client, key: &str, data: &[u8], mime_type: &str) -> Result<(), String> {
    client
        .execute(
            "INSERT INTO bot_assets (key, data, mime_type) VALUES ($1, $2, $3)
             ON CONFLICT (key) DO UPDATE SET data = $2, mime_type = $3, updated_at = NOW()",
            &[&key, &data, &mime_type],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

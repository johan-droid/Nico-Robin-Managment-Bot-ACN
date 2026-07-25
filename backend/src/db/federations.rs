use tokio_postgres::Client;

/// Creates a new federation.
pub async fn create_federation(
    client: &Client,
    fed_id: &str,
    name: &str,
    creator_id: i64,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO federations (fed_id, name, creator_id) VALUES ($1, $2, $3)"#,
        &[&fed_id, &name, &creator_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Joins a group to a federation.
pub async fn join_federation(
    client: &Client,
    fed_id: &str,
    group_id: i64,
) -> Result<bool, String> {
    let result = client.execute(
        r#"INSERT INTO federation_groups (fed_id, group_id) VALUES ($1, $2)
           ON CONFLICT DO NOTHING"#,
        &[&fed_id, &group_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(result > 0)
}

/// Checks if a federation exists.
pub async fn federation_exists(client: &Client, fed_id: &str) -> Result<bool, String> {
    let row = client.query_opt(
        r#"SELECT fed_id FROM federations WHERE fed_id = $1"#,
        &[&fed_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(row.is_some())
}

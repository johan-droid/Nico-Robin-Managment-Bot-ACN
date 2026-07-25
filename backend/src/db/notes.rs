use tokio_postgres::Client;

/// Saves a note for a group.
pub async fn save_note(
    client: &Client,
    group_id: i64,
    name: &str,
    content: &str,
    created_by: i64,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO notes (group_id, name, content, created_by)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id, name) DO UPDATE SET content = $3"#,
        &[&group_id, &name, &content, &created_by]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Gets a note by name for a group.
pub async fn get_note(
    client: &Client,
    group_id: i64,
    name: &str,
) -> Result<Option<String>, String> {
    let row = client.query_opt(
        r#"SELECT content FROM notes WHERE group_id = $1 AND name = $2"#,
        &[&group_id, &name]
    )
    .await
    .map_err(|e| e.to_string())?;

    Ok(row.map(|r| r.get(0)))
}

/// Lists all notes for a group.
pub async fn list_notes(client: &Client, group_id: i64) -> Result<Vec<String>, String> {
    let rows = client.query(
        r#"SELECT name FROM notes WHERE group_id = $1 ORDER BY name"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;

    Ok(rows.into_iter().map(|r| r.get(0)).collect())
}

/// Deletes a note by name for a group.
pub async fn delete_note(client: &Client, group_id: i64, name: &str) -> Result<bool, String> {
    let result = client.execute(
        r#"DELETE FROM notes WHERE group_id = $1 AND name = $2"#,
        &[&group_id, &name]
    )
    .await
    .map_err(|e| e.to_string())?;

    Ok(result > 0)
}

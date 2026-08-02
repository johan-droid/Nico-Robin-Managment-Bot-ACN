use tokio_postgres::Client;

/// Saves a note for a group.
pub async fn save_note(
    client: &Client,
    group_id: i64,
    name: &str,
    content: &str,
    created_by: i64,
) -> Result<(), String> {
    let _ = crate::db::groups::ensure_group(client, group_id, "Group").await;
    let lower_name = name.to_lowercase();
    let name_enc = crate::crypto::try_encrypt(&lower_name);
    let name_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower_name))
        .unwrap_or_default();
    let content_enc = crate::crypto::try_encrypt(content);

    // Check if the note already exists
    let exists: bool = if name_hash.is_empty() {
        client
            .query_one(
                "SELECT EXISTS(SELECT 1 FROM notes WHERE group_id = $1 AND name = $2)",
                &[&group_id, &name_enc],
            )
            .await
            .map_err(|e| e.to_string())?
            .get(0)
    } else {
        client
            .query_one(
                "SELECT EXISTS(SELECT 1 FROM notes WHERE group_id = $1 AND name_hash = $2)",
                &[&group_id, &name_hash],
            )
            .await
            .map_err(|e| e.to_string())?
            .get(0)
    };

    if exists {
        if name_hash.is_empty() {
            client
                .execute(
                    r#"UPDATE notes SET content = $1 WHERE group_id = $2 AND name = $3"#,
                    &[&content_enc, &group_id, &name_enc],
                )
                .await
                .map_err(|e| e.to_string())?;
        } else {
            client
                .execute(
                    r#"UPDATE notes SET content = $1 WHERE group_id = $2 AND name_hash = $3"#,
                    &[&content_enc, &group_id, &name_hash],
                )
                .await
                .map_err(|e| e.to_string())?;
        }
    } else {
        client
            .execute(
                r#"INSERT INTO notes (group_id, name, name_hash, content, created_by)
               VALUES ($1, $2, $3, $4, $5)"#,
                &[&group_id, &name_enc, &name_hash, &content_enc, &created_by],
            )
            .await
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Gets a note by name for a group.
pub async fn get_note(
    client: &Client,
    group_id: i64,
    name: &str,
) -> Result<Option<String>, String> {
    let lower_name = name.to_lowercase();
    let name_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower_name))
        .unwrap_or_default();
    
    let row = if name_hash.is_empty() {
        let name_enc = crate::crypto::try_encrypt(&lower_name);
        client
            .query_opt(
                r#"SELECT content FROM notes WHERE group_id = $1 AND name = $2"#,
                &[&group_id, &name_enc],
            )
            .await
            .map_err(|e| e.to_string())?
    } else {
        client
            .query_opt(
                r#"SELECT content FROM notes WHERE group_id = $1 AND name_hash = $2"#,
                &[&group_id, &name_hash],
            )
            .await
            .map_err(|e| e.to_string())?
    };

    Ok(row.map(|r| crate::crypto::try_decrypt(&r.get::<_, String>(0))))
}

/// Lists all notes for a group.
pub async fn list_notes(client: &Client, group_id: i64) -> Result<Vec<String>, String> {
    let rows = client
        .query(
            r#"SELECT name FROM notes WHERE group_id = $1"#,
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;

    let mut names: Vec<String> = rows.into_iter()
        .map(|r| crate::crypto::try_decrypt(&r.get::<_, String>(0)))
        .collect();
    names.sort();
    Ok(names)
}

/// Deletes a note by name for a group.
pub async fn delete_note(client: &Client, group_id: i64, name: &str) -> Result<bool, String> {
    let lower_name = name.to_lowercase();
    let name_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower_name))
        .unwrap_or_default();
    
    let result = if name_hash.is_empty() {
        let name_enc = crate::crypto::try_encrypt(&lower_name);
        client
            .execute(
                r#"DELETE FROM notes WHERE group_id = $1 AND name = $2"#,
                &[&group_id, &name_enc],
            )
            .await
            .map_err(|e| e.to_string())?
    } else {
        client
            .execute(
                r#"DELETE FROM notes WHERE group_id = $1 AND name_hash = $2"#,
                &[&group_id, &name_hash],
            )
            .await
            .map_err(|e| e.to_string())?
    };

    Ok(result > 0)
}

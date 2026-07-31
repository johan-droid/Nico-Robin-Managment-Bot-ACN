use tokio_postgres::Client;

#[derive(Clone)]
pub struct Filter {
    pub trigger_text: String,
    pub response: String,
}

pub async fn add_filter(
    client: &Client,
    group_id: i64,
    trigger_text: &str,
    response: &str,
    created_by: i64,
) -> Result<(), String> {
    let response_enc = crate::crypto::try_encrypt(response);
    client
        .execute(
            r#"INSERT INTO filters (group_id, trigger_text, response, created_by)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id, trigger_text) DO UPDATE SET response = $3"#,
            &[&group_id, &trigger_text, &response_enc, &created_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn list_filters(client: &Client, group_id: i64) -> Result<Vec<Filter>, String> {
    let rows = client.query(
        r#"SELECT trigger_text, response FROM filters WHERE group_id = $1 ORDER BY trigger_text"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;

    Ok(rows
        .into_iter()
        .map(|row| Filter {
            trigger_text: row.get(0),
            response: crate::crypto::try_decrypt(&row.get::<_, String>(1)),
        })
        .collect())
}

/// Checks if a message text matches any filter trigger and returns the response.
pub async fn check_filter(
    client: &Client,
    group_id: i64,
    text: &str,
) -> Result<Option<String>, String> {
    let text_lower = text.to_lowercase();
    let rows = client
        .query(
            r#"SELECT trigger_text, response FROM filters WHERE group_id = $1"#,
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;

    for row in rows {
        let trigger: String = row.get(0);
        let response: String = crate::crypto::try_decrypt(&row.get::<_, String>(1));
        if text_lower.contains(&trigger.to_lowercase()) {
            return Ok(Some(response));
        }
    }
    Ok(None)
}

pub async fn remove_filter(
    client: &Client,
    group_id: i64,
    trigger_text: &str,
) -> Result<bool, String> {
    let result = client
        .execute(
            r#"DELETE FROM filters WHERE group_id = $1 AND trigger_text = $2"#,
            &[&group_id, &trigger_text],
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(result > 0)
}

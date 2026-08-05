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
    if response.len() > 4000 {
        return Err("Filter response is too long (max 4000 characters).".to_string());
    }
    let _ = crate::db::groups::ensure_group(client, group_id, "Group").await;
    let lower_trigger = trigger_text.to_lowercase();
    let trigger_enc = crate::crypto::try_encrypt(&lower_trigger);
    let trigger_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower_trigger))
        .unwrap_or_default();
    let response_enc = crate::crypto::try_encrypt(response);

    let exists: bool = if trigger_hash.is_empty() {
        client
            .query_one(
                "SELECT EXISTS(SELECT 1 FROM filters WHERE group_id = $1 AND trigger_text = $2)",
                &[&group_id, &trigger_enc],
            )
            .await
            .map_err(|e| e.to_string())?
            .get(0)
    } else {
        client
            .query_one(
                "SELECT EXISTS(SELECT 1 FROM filters WHERE group_id = $1 AND trigger_hash = $2)",
                &[&group_id, &trigger_hash],
            )
            .await
            .map_err(|e| e.to_string())?
            .get(0)
    };

    if exists {
        if trigger_hash.is_empty() {
            client
                .execute(
                    r#"UPDATE filters SET response = $1 WHERE group_id = $2 AND trigger_text = $3"#,
                    &[&response_enc, &group_id, &trigger_enc],
                )
                .await
                .map_err(|e| e.to_string())?;
        } else {
            client
                .execute(
                    r#"UPDATE filters SET response = $1 WHERE group_id = $2 AND trigger_hash = $3"#,
                    &[&response_enc, &group_id, &trigger_hash],
                )
                .await
                .map_err(|e| e.to_string())?;
        }
    } else {
        // NULL instead of "" when crypto is off, so the partial unique index
        // (idx_filters_group_trigger_hash WHERE trigger_hash IS NOT NULL) does
        // not force every distinct filter in the group onto one free slot.
        let trigger_hash_param = if trigger_hash.is_empty() {
            None
        } else {
            Some(trigger_hash.clone())
        };
        let count: i64 = client
            .query_one(
                "SELECT COUNT(*) FROM filters WHERE group_id = $1",
                &[&group_id],
            )
            .await
            .map_err(|e| e.to_string())?
            .get(0);
        if count >= 200 {
            return Err("Filter limit reached (max 200 filters per group).".to_string());
        }
        client
            .execute(
                r#"INSERT INTO filters (group_id, trigger_text, trigger_hash, response, created_by)
               VALUES ($1, $2, $3, $4, $5)"#,
                &[
                    &group_id,
                    &trigger_enc,
                    &trigger_hash_param,
                    &response_enc,
                    &created_by,
                ],
            )
            .await
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

pub async fn list_filters(client: &Client, group_id: i64) -> Result<Vec<Filter>, String> {
    let rows = client
        .query(
            r#"SELECT trigger_text, response FROM filters WHERE group_id = $1"#,
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;

    let mut filters: Vec<Filter> = rows
        .into_iter()
        .map(|row| Filter {
            trigger_text: crate::crypto::try_decrypt(&row.get::<_, String>(0)),
            response: crate::crypto::try_decrypt(&row.get::<_, String>(1)),
        })
        .collect();
    filters.sort_by(|a, b| a.trigger_text.cmp(&b.trigger_text));
    Ok(filters)
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
        let trigger: String = crate::crypto::try_decrypt(&row.get::<_, String>(0));
        let response: String = crate::crypto::try_decrypt(&row.get::<_, String>(1));
        if crate::utils::contains_word(&text_lower, &trigger.to_lowercase()) {
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
    let lower_trigger = trigger_text.to_lowercase();
    let trigger_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower_trigger))
        .unwrap_or_default();

    let result = if trigger_hash.is_empty() {
        let trigger_enc = crate::crypto::try_encrypt(&lower_trigger);
        client
            .execute(
                r#"DELETE FROM filters WHERE group_id = $1 AND trigger_text = $2"#,
                &[&group_id, &trigger_enc],
            )
            .await
            .map_err(|e| e.to_string())?
    } else {
        client
            .execute(
                r#"DELETE FROM filters WHERE group_id = $1 AND trigger_hash = $2"#,
                &[&group_id, &trigger_hash],
            )
            .await
            .map_err(|e| e.to_string())?
    };

    Ok(result > 0)
}

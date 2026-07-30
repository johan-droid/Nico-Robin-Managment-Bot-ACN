use tokio_postgres::Client;

pub async fn add_swear(client: &Client, group_id: i64, word: &str) -> Result<(), String> {
    let lower = word.to_lowercase();
    let word_enc = crate::crypto::try_encrypt(&lower);
    let word_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower))
        .unwrap_or_default();
    client
        .execute(
            r#"INSERT INTO swear_words (group_id, word, word_hash) VALUES ($1, $2, $3)
           ON CONFLICT (group_id, word_hash) DO NOTHING"#,
            &[&group_id, &word_enc, &word_hash],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Checks if a message text contains any swear words for a group.
pub async fn check_swear(
    client: &Client,
    group_id: i64,
    text: &str,
) -> Result<Option<String>, String> {
    let text_lower = text.to_lowercase();
    let rows = client.query(
        r#"SELECT word FROM swear_words WHERE group_id = $1"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;

    for row in rows {
        let word: String = crate::crypto::try_decrypt(&row.get::<_, String>(0));
        if text_lower.contains(&word) {
            return Ok(Some(word));
        }
    }
    Ok(None)
}

pub async fn remove_swear(client: &Client, group_id: i64, word: &str) -> Result<bool, String> {
    let lower = word.to_lowercase();
    let word_hash = crate::crypto::try_crypto()
        .map(|c| c.hash_text(&lower))
        .unwrap_or_default();
    let result = if word_hash.is_empty() {
        client
            .execute(
                r#"DELETE FROM swear_words WHERE group_id = $1 AND word = $2"#,
                &[&group_id, &lower],
            )
            .await
            .map_err(|e| e.to_string())?
    } else {
        client
            .execute(
                r#"DELETE FROM swear_words WHERE group_id = $1 AND word_hash = $2"#,
                &[&group_id, &word_hash],
            )
            .await
            .map_err(|e| e.to_string())?
    };
    Ok(result > 0)
}

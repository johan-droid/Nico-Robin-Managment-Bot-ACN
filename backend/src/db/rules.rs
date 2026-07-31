use tokio_postgres::Client;

/// Sets the rules for a group (upsert).
pub async fn set_rules(
    client: &Client,
    group_id: i64,
    rules: &str,
    updated_by: i64,
) -> Result<(), String> {
    let rules_enc = crate::crypto::try_encrypt(rules);
    client
        .execute(
            r#"INSERT INTO group_rules (group_id, rules, updated_by, updated_at)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (group_id) DO UPDATE SET rules = $2, updated_by = $3, updated_at = NOW()"#,
            &[&group_id, &rules_enc, &updated_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Returns the rules for a group, if set.
pub async fn get_rules(client: &Client, group_id: i64) -> Result<Option<String>, String> {
    let row = client
        .query_opt(
            "SELECT rules FROM group_rules WHERE group_id = $1",
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.map(|r| crate::crypto::try_decrypt(&r.get::<_, String>(0))))
}

/// Removes the rules for a group. Returns true if rules existed.
pub async fn clear_rules(client: &Client, group_id: i64) -> Result<bool, String> {
    let result = client
        .execute("DELETE FROM group_rules WHERE group_id = $1", &[&group_id])
        .await
        .map_err(|e| e.to_string())?;
    Ok(result > 0)
}

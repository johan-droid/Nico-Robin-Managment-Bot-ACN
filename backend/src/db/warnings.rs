use tokio_postgres::Client;

/// Adds a warning for a user in a group.
pub async fn add_warning(
    client: &Client,
    group_id: i64,
    user_id: i64,
    reason: &str,
    warned_by: i64,
) -> Result<i32, String> {
    let reason_enc = crate::crypto::try_encrypt(reason);
    let row = client
        .query_one(
            r#"INSERT INTO warnings (group_id, user_id, reason, warned_by)
           VALUES ($1, $2, $3, $4) RETURNING id"#,
            &[&group_id, &user_id, &reason_enc, &warned_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.get(0))
}

/// Gets the warning count for a user in a group.
pub async fn get_warning_count(
    client: &Client,
    group_id: i64,
    user_id: i64,
) -> Result<i64, String> {
    let row = client
        .query_one(
            r#"SELECT COUNT(*) FROM warnings WHERE group_id = $1 AND user_id = $2"#,
            &[&group_id, &user_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.get(0))
}

/// Gets all warnings for a user in a group.
pub async fn get_warnings(
    client: &Client,
    group_id: i64,
    user_id: i64,
) -> Result<Vec<(i32, String, i64)>, String> {
    let rows = client
        .query(
            r#"SELECT id, reason, warned_by FROM warnings
           WHERE group_id = $1 AND user_id = $2 ORDER BY created_at"#,
            &[&group_id, &user_id],
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(rows
        .into_iter()
        .map(|row| {
            let id: i32 = row.get(0);
            let reason: String = crate::crypto::try_decrypt(&row.get::<_, String>(1));
            let warned_by: i64 = row.get(2);
            (id, reason, warned_by)
        })
        .collect())
}

/// Resets all warnings for a user in a group.
pub async fn reset_warnings(client: &Client, group_id: i64, user_id: i64) -> Result<u64, String> {
    let result = client
        .execute(
            r#"DELETE FROM warnings WHERE group_id = $1 AND user_id = $2"#,
            &[&group_id, &user_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(result)
}

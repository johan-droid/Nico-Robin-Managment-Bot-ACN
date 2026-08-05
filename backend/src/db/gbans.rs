use tokio_postgres::Client;

#[derive(Clone, Debug)]
pub struct Gban {
    pub user_id: i64,
    pub user_name: String,
    pub reason: String,
    pub banned_by: i64,
}

/// Adds a user to the global ban list.
pub async fn add_gban(
    client: &Client,
    user_id: i64,
    user_name: &str,
    reason: &str,
    banned_by: i64,
) -> Result<(), String> {
    let name_enc = crate::crypto::try_encrypt(user_name);
    let reason_enc = crate::crypto::try_encrypt(reason);
    client
        .execute(
            r#"INSERT INTO gbans (user_id, user_name, reason, banned_by, banned_at)
               VALUES ($1, $2, $3, $4, NOW())
               ON CONFLICT (user_id) DO UPDATE SET user_name = $2, reason = $3, banned_by = $4, banned_at = NOW()"#,
            &[&user_id, &name_enc, &reason_enc, &banned_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Removes a user from the global ban list. Returns true if they were gbanned.
pub async fn remove_gban(client: &Client, user_id: i64) -> Result<bool, String> {
    let result = client
        .execute("DELETE FROM gbans WHERE user_id = $1", &[&user_id])
        .await
        .map_err(|e| e.to_string())?;
    Ok(result > 0)
}

/// Returns the gban record for a user, if any.
pub async fn get_gban(client: &Client, user_id: i64) -> Result<Option<Gban>, String> {
    let row = client
        .query_opt(
            "SELECT user_id, user_name, reason, banned_by FROM gbans WHERE user_id = $1",
            &[&user_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.map(|r| Gban {
        user_id: r.get(0),
        user_name: crate::crypto::try_decrypt(&r.get::<_, String>(1)),
        reason: crate::crypto::try_decrypt(&r.get::<_, String>(2)),
        banned_by: r.get(3),
    }))
}

/// Returns the most recent gbans (capped so a huge list can't blow the
/// message-length limit or memory).
pub async fn list_gbans(client: &Client) -> Result<Vec<Gban>, String> {
    let rows = client
        .query(
            "SELECT user_id, user_name, reason, banned_by FROM gbans ORDER BY banned_at DESC LIMIT 50",
            &[],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(rows
        .into_iter()
        .map(|r| Gban {
            user_id: r.get(0),
            user_name: crate::crypto::try_decrypt(&r.get::<_, String>(1)),
            reason: crate::crypto::try_decrypt(&r.get::<_, String>(2)),
            banned_by: r.get(3),
        })
        .collect())
}

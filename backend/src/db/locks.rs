use tokio_postgres::Client;

/// Checks if a lock type is enabled for a group.
pub async fn is_locked(client: &Client, group_id: i64, lock_type: &str) -> Result<bool, String> {
    let row = client
        .query_opt(
            "SELECT enabled FROM group_locks WHERE group_id = $1 AND lock_type = $2",
            &[&group_id, &lock_type],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.map(|r| r.get::<usize, bool>(0)).unwrap_or(false))
}

/// Enables a lock for a group.
pub async fn lock_group(
    client: &Client,
    group_id: i64,
    lock_type: &str,
    toggled_by: i64,
) -> Result<(), String> {
    let _ = crate::db::groups::ensure_group(client, group_id, "Group").await;
    client
        .execute(
            r#"INSERT INTO group_locks (group_id, lock_type, enabled, toggled_by, toggled_at)
               VALUES ($1, $2, TRUE, $3, NOW())
               ON CONFLICT (group_id, lock_type) DO UPDATE SET enabled = TRUE, toggled_by = $3, toggled_at = NOW()"#,
            &[&group_id, &lock_type, &toggled_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Disables a lock for a group.
pub async fn unlock_group(
    client: &Client,
    group_id: i64,
    lock_type: &str,
    toggled_by: i64,
) -> Result<(), String> {
    let _ = crate::db::groups::ensure_group(client, group_id, "Group").await;
    client
        .execute(
            r#"INSERT INTO group_locks (group_id, lock_type, enabled, toggled_by, toggled_at)
               VALUES ($1, $2, FALSE, $3, NOW())
               ON CONFLICT (group_id, lock_type) DO UPDATE SET enabled = FALSE, toggled_by = $3, toggled_at = NOW()"#,
            &[&group_id, &lock_type, &toggled_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Lists all locks for a group (only those explicitly toggled).
pub async fn list_locks(client: &Client, group_id: i64) -> Result<Vec<(String, bool)>, String> {
    let rows = client
        .query(
            "SELECT lock_type, enabled FROM group_locks WHERE group_id = $1 ORDER BY lock_type",
            &[&group_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(rows
        .into_iter()
        .map(|row| (row.get(0), row.get(1)))
        .collect())
}

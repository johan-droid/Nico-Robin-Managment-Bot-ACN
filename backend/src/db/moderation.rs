use tokio_postgres::Client;
use chrono::{Utc, TimeZone};

pub async fn add_mute(client: &Client, group_id: i64, user_id: i64, reason: &str, muted_by: i64) -> Result<(), String> {
    client.execute(
        "INSERT INTO mutes (group_id, user_id, reason, muted_by) VALUES ($1, $2, $3, $4) ON CONFLICT (group_id, user_id) DO UPDATE SET reason = $3, muted_by = $4, muted_at = NOW()",
        &[&group_id, &user_id, &reason, &muted_by],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn remove_mute(client: &Client, group_id: i64, user_id: i64) -> Result<(), String> {
    client.execute(
        "DELETE FROM mutes WHERE group_id = $1 AND user_id = $2",
        &[&group_id, &user_id],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn add_temp_mute(client: &Client, group_id: i64, user_id: i64, reason: &str, muted_by: i64, expires_at_ts: i64) -> Result<(), String> {
    let expires_at = Utc.timestamp_opt(expires_at_ts, 0).single().unwrap_or_else(Utc::now);
    client.execute(
        "INSERT INTO temp_mutes (group_id, user_id, reason, muted_by, expires_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (group_id, user_id) DO UPDATE SET reason = $3, muted_by = $4, muted_at = NOW(), expires_at = $5",
        &[&group_id, &user_id, &reason, &muted_by, &expires_at],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn remove_temp_mute(client: &Client, group_id: i64, user_id: i64) -> Result<(), String> {
    client.execute(
        "DELETE FROM temp_mutes WHERE group_id = $1 AND user_id = $2",
        &[&group_id, &user_id],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn add_temp_ban(client: &Client, group_id: i64, user_id: i64, reason: &str, banned_by: i64, expires_at_ts: i64) -> Result<(), String> {
    let expires_at = Utc.timestamp_opt(expires_at_ts, 0).single().unwrap_or_else(Utc::now);
    client.execute(
        "INSERT INTO temp_bans (group_id, user_id, reason, banned_by, expires_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (group_id, user_id) DO UPDATE SET reason = $3, banned_by = $4, banned_at = NOW(), expires_at = $5",
        &[&group_id, &user_id, &reason, &banned_by, &expires_at],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn remove_temp_ban(client: &Client, group_id: i64, user_id: i64) -> Result<(), String> {
    client.execute(
        "DELETE FROM temp_bans WHERE group_id = $1 AND user_id = $2",
        &[&group_id, &user_id],
    ).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn get_expired_temp_mutes(client: &Client) -> Result<Vec<(i64, i64)>, String> {
    let rows = client.query(
        "SELECT group_id, user_id FROM temp_mutes WHERE expires_at <= NOW()",
        &[]
    ).await.map_err(|e| e.to_string())?;
    Ok(rows.iter().map(|r| (r.get(0), r.get(1))).collect())
}

pub async fn get_expired_temp_bans(client: &Client) -> Result<Vec<(i64, i64)>, String> {
    let rows = client.query(
        "SELECT group_id, user_id FROM temp_bans WHERE expires_at <= NOW()",
        &[]
    ).await.map_err(|e| e.to_string())?;
    Ok(rows.iter().map(|r| (r.get(0), r.get(1))).collect())
}

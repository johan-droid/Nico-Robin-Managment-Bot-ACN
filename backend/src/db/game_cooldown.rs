use tokio_postgres::Client;

/// Default game-specific cooldown durations (in seconds).
pub fn cooldown_for(game_type: &str) -> i32 {
    match game_type {
        "voyage" => 3600,        // 1 hour
        "quiz" => 300,           // 5 minutes
        "bounty_claim" => 86400, // 24 hours
        "crew_voyage" => 7200,   // 2 hours
        _ => 600,                // Default 10 mins
    }
}

/// Returns `Some(remaining_secs)` if the user is still inside the cooldown window
/// for the given game type, or `None` if they may play (first play or expired).
pub async fn check_cooldown(
    client: &Client,
    user_id: i64,
    game_type: &str,
    cooldown_secs: i32,
) -> Result<Option<i32>, String> {
    if let Some(remaining) = remaining_for(client, user_id, game_type, cooldown_secs).await? {
        if remaining > 0 {
            return Ok(Some(remaining));
        }
    }
    Ok(None)
}

/// Records a play for the user, resetting the cooldown timestamp for the game type.
/// The stored `cooldown_seconds` column is kept in sync so `/cooldown` can report it.
pub async fn set_cooldown(client: &Client, user_id: i64, game_type: &str) -> Result<(), String> {
    let cooldown_secs = cooldown_for(game_type);
    let stmt = client
        .prepare(
            "INSERT INTO game_cooldowns (user_id, game_type, last_played_at, cooldown_seconds)
             VALUES ($1, $2, NOW(), $3)
             ON CONFLICT (user_id, game_type)
             DO UPDATE SET last_played_at = NOW(), cooldown_seconds = EXCLUDED.cooldown_seconds",
        )
        .await
        .map_err(|e| format!("Failed to prepare cooldown query: {}", e))?;

    client
        .execute(&stmt, &[&user_id, &game_type, &cooldown_secs])
        .await
        .map_err(|e| format!("Failed to record cooldown: {}", e))?;

    Ok(())
}

/// Remaining cooldown in seconds (0 if the user may play now). Never negative.
pub async fn get_remaining_cooldown(
    client: &Client,
    user_id: i64,
    game_type: &str,
) -> Result<i32, String> {
    let cooldown_secs = cooldown_for(game_type);
    Ok(remaining_for(client, user_id, game_type, cooldown_secs)
        .await?
        .unwrap_or(0))
}

/// Removes the cooldown record entirely (used by the `/resetcooldown` admin command).
/// Returns true if a record existed and was removed.
pub async fn reset_cooldown(
    client: &Client,
    user_id: i64,
    game_type: &str,
) -> Result<bool, String> {
    let stmt = client
        .prepare("DELETE FROM game_cooldowns WHERE user_id = $1 AND game_type = $2")
        .await
        .map_err(|e| e.to_string())?;
    let deleted = client
        .execute(&stmt, &[&user_id, &game_type])
        .await
        .map_err(|e| e.to_string())?;
    Ok(deleted > 0)
}

/// All active cooldowns for a user as `(game_type, remaining_secs)`, for `/cooldown`.
pub async fn list_cooldowns(
    client: &Client,
    user_id: i64,
) -> Result<Vec<(String, i32)>, String> {
    let stmt = client
        .prepare(
            "SELECT game_type,
                    GREATEST(cooldown_seconds - EXTRACT(EPOCH FROM (NOW() - last_played_at))::INT, 0)::INT AS remaining
             FROM game_cooldowns
             WHERE user_id = $1
             ORDER BY remaining DESC",
        )
        .await
        .map_err(|e| e.to_string())?;

    let rows = client
        .query(&stmt, &[&user_id])
        .await
        .map_err(|e| e.to_string())?;

    let mut cooldowns = Vec::new();
    for row in rows {
        let remaining: i32 = row.get(1);
        if remaining > 0 {
            cooldowns.push((row.get(0), remaining));
        }
    }
    Ok(cooldowns)
}

async fn remaining_for(
    client: &Client,
    user_id: i64,
    game_type: &str,
    cooldown_secs: i32,
) -> Result<Option<i32>, String> {
    let stmt = client
        .prepare(
            "SELECT GREATEST($3 - EXTRACT(EPOCH FROM (NOW() - last_played_at))::INT, 0)::INT AS remaining
             FROM game_cooldowns
             WHERE user_id = $1 AND game_type = $2",
        )
        .await
        .map_err(|e| e.to_string())?;

    let row_opt = client
        .query_opt(&stmt, &[&user_id, &game_type, &cooldown_secs])
        .await
        .map_err(|e| e.to_string())?;

    Ok(row_opt.map(|row| row.get::<_, i32>(0)))
}

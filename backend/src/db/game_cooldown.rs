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

/// Atomically claims the cooldown slot for `game_type`, if available.
///
/// This is the authoritative gate for paid gameplay. The check-and-claim is
/// race-free:
///  1. `UPDATE ... WHERE last_played_at <= expiry` takes a row lock, so
///     concurrent calls serialize on the row and the loser sees the fresh
///     timestamp and fails the predicate.
///  2. If no row exists yet, a bare `INSERT ... ON CONFLICT DO NOTHING` lets
///     exactly one concurrent caller win.
/// Returns `true` when the slot was claimed (game may proceed), `false` when
/// the user is still inside their cooldown window.
pub async fn try_consume_cooldown(
    client: &Client,
    user_id: i64,
    game_type: &str,
) -> Result<bool, String> {
    let cooldown_secs = cooldown_for(game_type);

    // Expired record present -> atomically refresh it.
    // PostgreSQL has no `interval * integer` operator — interval multiplication
    // only exists with FLOAT8. `$4` is therefore sent as f64 (always an exact
    // integer, so the round-trip is lossless) while `$3` stays i32 for the INT
    // column. Using two parameters avoids any server-side type inference on a
    // single $n used in both int4 and float8 contexts.
    let updated = client
        .execute(
            "UPDATE game_cooldowns
             SET last_played_at = NOW(), cooldown_seconds = $3
             WHERE user_id = $1 AND game_type = $2
               AND last_played_at <= NOW() - ($4 * interval '1 second')",
            &[&user_id, &game_type, &cooldown_secs, &(cooldown_secs as f64)],
        )
        .await
        .map_err(|e| format!("Failed to consume cooldown: {}", e))?;
    if updated > 0 {
        return Ok(true);
    }

    // No row (or not expired). Try to insert a fresh record; only one of any
    // concurrent callers can win the conflict.
    let inserted = client
        .execute(
            "INSERT INTO game_cooldowns (user_id, game_type, last_played_at, cooldown_seconds)
             VALUES ($1, $2, NOW(), $3)
             ON CONFLICT (user_id, game_type) DO NOTHING",
            &[&user_id, &game_type, &cooldown_secs],
        )
        .await
        .map_err(|e| format!("Failed to create cooldown record: {}", e))?;

    Ok(inserted > 0)
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

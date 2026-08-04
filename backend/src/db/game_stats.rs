use tokio_postgres::Client;

#[derive(Debug, Clone)]
pub struct GameStats {
    pub game_type: String,
    pub plays: i32,
    pub wins: i32,
}

/// Records a play for a game type and increments `wins` when the play succeeded.
pub async fn record_game_play(
    client: &Client,
    user_id: i64,
    game_type: &str,
    win: bool,
) -> Result<(), String> {
    let stmt = client
        .prepare(
            "INSERT INTO game_stats (user_id, game_type, plays, wins)
             VALUES ($1, $2, 1, $3)
             ON CONFLICT (user_id, game_type)
             DO UPDATE SET
                 plays = game_stats.plays + 1,
                 wins = game_stats.wins + EXCLUDED.wins,
                 updated_at = NOW()",
        )
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let win_count: i32 = if win { 1 } else { 0 };
    client
        .execute(&stmt, &[&user_id, &game_type, &win_count])
        .await
        .map_err(|e| format!("Failed to record game play: {}", e))?;

    Ok(())
}

/// Total play/win counts for a user (all game types combined).
pub async fn get_game_stats(client: &Client, user_id: i64) -> Result<(i32, i32), String> {
    let stmt = client
        .prepare(
            "SELECT COALESCE(SUM(plays), 0)::INT, COALESCE(SUM(wins), 0)::INT
             FROM game_stats WHERE user_id = $1",
        )
        .await
        .map_err(|e| e.to_string())?;

    let row = client
        .query_one(&stmt, &[&user_id])
        .await
        .map_err(|e| e.to_string())?;

    Ok((row.get(0), row.get(1)))
}

/// Breakdown of stats per game type for a user.
pub async fn get_game_stats_breakdown(
    client: &Client,
    user_id: i64,
) -> Result<Vec<GameStats>, String> {
    let stmt = client
        .prepare("SELECT game_type, plays, wins FROM game_stats WHERE user_id = $1 ORDER BY plays DESC")
        .await
        .map_err(|e| e.to_string())?;

    let rows = client
        .query(&stmt, &[&user_id])
        .await
        .map_err(|e| e.to_string())?;

    let mut stats = Vec::new();
    for row in rows {
        stats.push(GameStats {
            game_type: row.get(0),
            plays: row.get(1),
            wins: row.get(2),
        });
    }
    Ok(stats)
}

/// Detailed game history for the `/gamestats` admin audit command.
pub async fn get_user_game_history(
    client: &Client,
    user_id: i64,
) -> Result<Vec<(String, i32, i32, i32)>, String> {
    // game_type, plays, wins, win_rate (as a percentage)
    let stmt = client
        .prepare(
            "SELECT game_type, plays, wins,
                    CASE WHEN plays > 0 THEN (wins * 100 / plays)::INT ELSE 0 END AS win_rate
             FROM game_stats WHERE user_id = $1 ORDER BY plays DESC",
        )
        .await
        .map_err(|e| e.to_string())?;

    let rows = client
        .query(&stmt, &[&user_id])
        .await
        .map_err(|e| e.to_string())?;

    let mut history = Vec::new();
    for row in rows {
        history.push((row.get(0), row.get(1), row.get(2), row.get(3)));
    }
    Ok(history)
}

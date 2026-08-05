use std::collections::HashMap;
use tokio_postgres::Client;

#[derive(Debug, Clone)]
pub struct CrewRanking {
    pub rank: i32,
    pub crew_id: i32,
    pub crew_name: String,
    pub total_bounty: i64,
    pub member_count: i32,
    pub avg_bounty_per_member: i64,
    pub captain_name: String,
    pub total_voyages: i32,
}

#[derive(Debug, Clone)]
pub struct UserRanking {
    pub rank: i32,
    pub user_id: i64,
    pub bounty: i64,
    pub username: String,
    pub crew_name: String,
}

/// Top crews by total bounty with member count, average bounty, captain name
/// and aggregate voyage plays. Names come from `username_cache` and are decrypted
/// in Rust because `first_name` is stored encrypted.
pub async fn get_crew_leaderboard_detailed(
    client: &Client,
    limit: i64,
) -> Result<Vec<CrewRanking>, String> {
    let stmt = client
        .prepare(
            "SELECT
                ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(b.bounty), 0) DESC, c.id ASC) AS rank,
                c.id,
                c.name,
                COALESCE(SUM(b.bounty), 0) AS total_bounty,
                COUNT(DISTINCT m.user_id) AS member_count,
                CASE
                    WHEN COUNT(DISTINCT m.user_id) > 0
                    THEN COALESCE(SUM(b.bounty), 0) / COUNT(DISTINCT m.user_id)
                    ELSE 0
                END AS avg_bounty,
                c.captain_id,
                COALESCE((SELECT SUM(gs.plays) FROM game_stats gs
                          JOIN pirate_crew_members cm ON cm.user_id = gs.user_id
                          WHERE cm.crew_id = c.id AND gs.game_type = 'voyage'), 0) AS total_voyages
            FROM pirate_crews c
            LEFT JOIN pirate_crew_members m ON c.id = m.crew_id
            LEFT JOIN one_piece_bounties b ON m.user_id = b.user_id
            GROUP BY c.id, c.name, c.captain_id
            HAVING COALESCE(SUM(b.bounty), 0) > 0
            ORDER BY total_bounty DESC, c.id ASC
            LIMIT $1",
        )
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let rows = client
        .query(&stmt, &[&limit])
        .await
        .map_err(|e| e.to_string())?;

    let mut rankings = Vec::new();
    let mut captain_ids: Vec<i64> = Vec::new();
    for row in &rows {
        captain_ids.push(row.get::<_, i64>(6));
    }
    let names = resolve_user_names(client, &captain_ids).await;

    for row in rows {
        let captain_id: i64 = row.get(6);
        let crew_id: i32 = row.get(1);
        rankings.push(CrewRanking {
            rank: row.get(0),
            crew_id,
            crew_name: row.get(2),
            total_bounty: row.get(3),
            member_count: row.get(4),
            avg_bounty_per_member: row.get(5),
            captain_name: names
                .get(&captain_id)
                .cloned()
                .unwrap_or_else(|| format!("Captain #{}", captain_id)),
            total_voyages: row.get(7),
        });
    }
    Ok(rankings)
}

/// Top pirates by bounty with their crew affiliation (if any).
pub async fn get_user_leaderboard_detailed(
    client: &Client,
    limit: i64,
) -> Result<Vec<UserRanking>, String> {
    let stmt = client
        .prepare(
            "SELECT
                ROW_NUMBER() OVER (ORDER BY b.bounty DESC, b.user_id ASC) AS rank,
                b.user_id,
                b.bounty,
                COALESCE(c.name, 'Solo Pirate') AS crew_name
            FROM one_piece_bounties b
            LEFT JOIN pirate_crew_members m ON b.user_id = m.user_id
            LEFT JOIN pirate_crews c ON m.crew_id = c.id
            WHERE b.bounty > 0
            ORDER BY b.bounty DESC, b.user_id ASC
            LIMIT $1",
        )
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let rows = client
        .query(&stmt, &[&limit])
        .await
        .map_err(|e| e.to_string())?;

    let user_ids: Vec<i64> = rows.iter().map(|row| row.get::<_, i64>(1)).collect();
    let names = resolve_user_names(client, &user_ids).await;

    let mut lb = Vec::new();
    for row in rows {
        let user_id: i64 = row.get(1);
        lb.push(UserRanking {
            rank: row.get(0),
            user_id,
            bounty: row.get(2),
            username: names
                .get(&user_id)
                .cloned()
                .unwrap_or_else(|| format!("Pirate #{}", user_id)),
            crew_name: row.get(3),
        });
    }
    Ok(lb)
}

/// Aggregate stats + global rank for a single crew (`/crewstats`).
pub async fn get_crew_stats(
    client: &Client,
    crew_id: i32,
) -> Result<Option<CrewRanking>, String> {
    let stmt = client
        .prepare(
            "SELECT
                ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(b.bounty), 0) DESC, c.id ASC) AS rank,
                c.id,
                c.name,
                COALESCE(SUM(b.bounty), 0) AS total_bounty,
                COUNT(DISTINCT m.user_id) AS member_count,
                CASE
                    WHEN COUNT(DISTINCT m.user_id) > 0
                    THEN COALESCE(SUM(b.bounty), 0) / COUNT(DISTINCT m.user_id)
                    ELSE 0
                END AS avg_bounty,
                c.captain_id,
                COALESCE((SELECT SUM(gs.plays) FROM game_stats gs
                          JOIN pirate_crew_members cm ON cm.user_id = gs.user_id
                          WHERE cm.crew_id = c.id AND gs.game_type = 'voyage'), 0) AS total_voyages
            FROM pirate_crews c
            LEFT JOIN pirate_crew_members m ON c.id = m.crew_id
            LEFT JOIN one_piece_bounties b ON m.user_id = b.user_id
            WHERE c.id = $1
            GROUP BY c.id, c.name, c.captain_id",
        )
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let row_opt = client
        .query_opt(&stmt, &[&crew_id])
        .await
        .map_err(|e| e.to_string())?;

    let Some(row) = row_opt else {
        return Ok(None);
    };

    let captain_id: i64 = row.get(6);
    let names = resolve_user_names(client, &[captain_id]).await;

    Ok(Some(CrewRanking {
        rank: row.get(0),
        crew_id: row.get(1),
        crew_name: row.get(2),
        total_bounty: row.get(3),
        member_count: row.get(4),
        avg_bounty_per_member: row.get(5),
        captain_name: names
            .get(&captain_id)
            .cloned()
            .unwrap_or_else(|| format!("Captain #{}", captain_id)),
        total_voyages: row.get(7),
    }))
}

/// Resolves display names for a batch of user IDs from `username_cache`.
/// `first_name` is stored encrypted, so each entry is decrypted before use.
pub(crate) async fn resolve_user_names(client: &Client, user_ids: &[i64]) -> HashMap<i64, String> {
    if user_ids.is_empty() {
        return HashMap::new();
    }
    let stmt = match client
        .prepare(
            "SELECT DISTINCT ON (user_id) user_id, first_name
             FROM username_cache
             WHERE user_id = ANY($1)
             ORDER BY user_id, updated_at DESC",
        )
        .await
    {
        Ok(s) => s,
        Err(_) => return HashMap::new(),
    };

    let mut names = HashMap::new();
    match client.query(&stmt, &[&user_ids]).await {
        Ok(rows) => {
            for row in rows {
                let user_id: i64 = row.get(0);
                let name: String = row.get(1);
                let name = crate::crypto::try_decrypt(&name);
                names.insert(user_id, name);
            }
        }
        Err(_) => {}
    }
    names
}

/// Wipes every bounty in the Wanted Ledger (`/leaderboard reset`). Returns the
/// number of records cleared.
pub async fn reset_all_bounties(client: &Client) -> Result<u64, String> {
    client
        .execute("DELETE FROM one_piece_bounties", &[])
        .await
        .map_err(|e| e.to_string())
}

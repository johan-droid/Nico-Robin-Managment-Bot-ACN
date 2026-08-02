use tokio_postgres::Client;
use std::time::SystemTime;

pub async fn get_bounty(client: &Client, user_id: i64) -> Result<i64, String> {
    let stmt = client
        .prepare("SELECT bounty FROM one_piece_bounties WHERE user_id = $1")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;
    let row_opt = client
        .query_opt(&stmt, &[&user_id])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    if let Some(row) = row_opt {
        Ok(row.get::<_, i64>(0))
    } else {
        Ok(0)
    }
}

pub async fn add_bounty(client: &Client, user_id: i64, amount: i64) -> Result<i64, String> {
    let stmt = client
        .prepare("
            INSERT INTO one_piece_bounties (user_id, bounty)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET bounty = GREATEST(one_piece_bounties.bounty + EXCLUDED.bounty, 0)
            RETURNING bounty
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;
    let row = client
        .query_one(&stmt, &[&user_id, &amount])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    Ok(row.get::<_, i64>(0))
}

pub async fn get_leaderboard(client: &Client, limit: i64) -> Result<Vec<(i64, i64)>, String> {
    let stmt = client
        .prepare("SELECT user_id, bounty FROM one_piece_bounties ORDER BY bounty DESC LIMIT $1")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let rows = client.query(&stmt, &[&limit]).await.map_err(|e| e.to_string())?;

    let mut lb = Vec::new();
    for row in rows {
        lb.push((row.get(0), row.get(1)));
    }
    Ok(lb)
}

pub async fn get_crew_leaderboard(client: &Client, limit: i64) -> Result<Vec<(String, i64)>, String> {
    let stmt = client
        .prepare("
            SELECT c.name, COALESCE(SUM(b.bounty), 0) as crew_bounty
            FROM pirate_crews c
            LEFT JOIN pirate_crew_members m ON c.id = m.crew_id
            LEFT JOIN one_piece_bounties b ON m.user_id = b.user_id
            GROUP BY c.id, c.name
            ORDER BY crew_bounty DESC
            LIMIT $1
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let rows = client.query(&stmt, &[&limit]).await.map_err(|e| e.to_string())?;

    let mut lb = Vec::new();
    for row in rows {
        lb.push((row.get(0), row.get(1)));
    }
    Ok(lb)
}

pub async fn claim_daily_bounty(client: &Client, user_id: i64) -> Result<Result<i64, String>, String> {
    let stmt = client
        .prepare("
            INSERT INTO one_piece_bounties (user_id, bounty, last_daily_checkin)
            VALUES ($1, 5, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
                bounty = CASE
                    WHEN one_piece_bounties.last_daily_checkin IS NULL OR
                         EXTRACT(EPOCH FROM (NOW() - one_piece_bounties.last_daily_checkin)) >= 86400
                    THEN one_piece_bounties.bounty + 5
                    ELSE one_piece_bounties.bounty
                END,
                last_daily_checkin = CASE
                    WHEN one_piece_bounties.last_daily_checkin IS NULL OR
                         EXTRACT(EPOCH FROM (NOW() - one_piece_bounties.last_daily_checkin)) >= 86400
                    THEN NOW()
                    ELSE one_piece_bounties.last_daily_checkin
                END
            RETURNING bounty, EXTRACT(EPOCH FROM (NOW() - one_piece_bounties.last_daily_checkin)) AS elapsed
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let row = client
        .query_one(&stmt, &[&user_id])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    let bounty = row.get::<_, i64>(0);
    let elapsed: Option<f64> = row.get(1);

    if let Some(e) = elapsed {
        if e < 1.0 {
            return Ok(Ok(bounty));
        } else {
            let remaining = 86400.0 - e;
            return Ok(Err(format!("You already claimed your bounty! Try again in {:.0} hours.", remaining / 3600.0)));
        }
    }

    Ok(Ok(bounty))
}

pub async fn perform_voyage(client: &Client, user_id: i64) -> Result<Result<(i64, i64, String), String>, String> {
    let check_stmt = client.prepare("SELECT last_voyage, bounty FROM one_piece_bounties WHERE user_id = $1").await.map_err(|e| format!("DB Error: {}", e))?;
    let row_opt = client.query_opt(&check_stmt, &[&user_id]).await.map_err(|e| format!("DB Error: {}", e))?;

    if let Some(row) = row_opt {
        let last_voyage: Option<std::time::SystemTime> = row.try_get(0).unwrap_or(None);
        if let Some(lv) = last_voyage {
            let elapsed = SystemTime::now().duration_since(lv).unwrap_or(std::time::Duration::from_secs(0)).as_secs();
            if elapsed < 3600 {
                return Ok(Err(format!("Your crew is resting. You can sail again in {} minutes.", (3600 - elapsed) / 60)));
            }
        }
    }

    let roll = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap_or(std::time::Duration::from_secs(0))
        .subsec_nanos() % 100;

    let (change, msg) = match roll {
        0..=15 => (20, "You found hidden treasure!"),
        16..=40 => (12, "You discovered an abandoned island."),
        41..=60 => (8, "You rescued a stranded pirate."),
        61..=75 => (-5, "You were caught in a storm."),
        76..=90 => (-7, "A Sea Beast attacked your ship."),
        _ => (-10, "Marines ambushed your crew!"),
    };

    let stmt = client
        .prepare("
            INSERT INTO one_piece_bounties (user_id, bounty, last_voyage)
            VALUES ($1, GREATEST($2::BIGINT, 0::BIGINT), NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
                bounty = GREATEST(one_piece_bounties.bounty + $2, 0),
                last_voyage = NOW()
            RETURNING bounty
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let row = client
        .query_one(&stmt, &[&user_id, &change])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    let new_bounty = row.get::<_, i64>(0);

    Ok(Ok((change, new_bounty, msg.to_string())))
}

pub async fn create_crew(client: &Client, captain_id: i64, name: &str) -> Result<i32, String> {
    let stmt = client
        .prepare("INSERT INTO pirate_crews (name, captain_id) VALUES ($1, $2) RETURNING id")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    match client.query_one(&stmt, &[&name, &captain_id]).await {
        Ok(row) => {
            let crew_id: i32 = row.get(0);

            let member_stmt = client.prepare("INSERT INTO pirate_crew_members (crew_id, user_id) VALUES ($1, $2)").await.map_err(|e| e.to_string())?;
            let _ = client.execute(&member_stmt, &[&crew_id, &captain_id]).await.map_err(|e| e.to_string())?;

            Ok(crew_id)
        },
        Err(e) => {
            if e.to_string().contains("unique constraint") {
                Err("A crew with this name already exists!".to_string())
            } else {
                Err(format!("Database error: {}", e))
            }
        }
    }
}

pub async fn get_crew_by_member(client: &Client, user_id: i64) -> Result<Option<(i32, String, i64)>, String> {
    let stmt = client
        .prepare("
            SELECT c.id, c.name, c.captain_id
            FROM pirate_crews c
            JOIN pirate_crew_members m ON c.id = m.crew_id
            WHERE m.user_id = $1
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let row_opt = client
        .query_opt(&stmt, &[&user_id])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    if let Some(row) = row_opt {
        Ok(Some((row.get(0), row.get(1), row.get(2))))
    } else {
        Ok(None)
    }
}

pub async fn get_crew_bounty(client: &Client, crew_id: i32) -> Result<i64, String> {
    let stmt = client
        .prepare("
            SELECT COALESCE(SUM(b.bounty), 0)
            FROM pirate_crew_members m
            LEFT JOIN one_piece_bounties b ON m.user_id = b.user_id
            WHERE m.crew_id = $1
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let row = client
        .query_one(&stmt, &[&crew_id])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    Ok(row.get::<_, i64>(0))
}

pub async fn invite_to_crew(client: &Client, crew_id: i32, user_id: i64, inviter_id: i64) -> Result<(), String> {
    let stmt = client
        .prepare("
            INSERT INTO pirate_crew_invites (crew_id, user_id, invited_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (crew_id, user_id) DO NOTHING
        ")
        .await
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    client.execute(&stmt, &[&crew_id, &user_id, &inviter_id])
        .await
        .map_err(|e| format!("Failed to execute query: {}", e))?;

    Ok(())
}

pub async fn join_crew(client: &Client, user_id: i64, crew_id: i32) -> Result<(), String> {
    let check_stmt = client
        .prepare("SELECT 1 FROM pirate_crew_invites WHERE crew_id = $1 AND user_id = $2")
        .await.map_err(|e| e.to_string())?;

    let row_opt = client.query_opt(&check_stmt, &[&crew_id, &user_id]).await.map_err(|e| e.to_string())?;
    if row_opt.is_none() {
        return Err("You don't have an invitation to this crew!".to_string());
    }

    if get_crew_by_member(client, user_id).await?.is_some() {
        return Err("You are already in a crew! Leave it first to join a new one.".to_string());
    }

    let stmt = client
        .prepare("INSERT INTO pirate_crew_members (crew_id, user_id) VALUES ($1, $2)")
        .await.map_err(|e| e.to_string())?;

    client.execute(&stmt, &[&crew_id, &user_id]).await.map_err(|e| e.to_string())?;

    let del_stmt = client
        .prepare("DELETE FROM pirate_crew_invites WHERE user_id = $1")
        .await.map_err(|e| e.to_string())?;
    client.execute(&del_stmt, &[&user_id]).await.map_err(|e| e.to_string())?;

    Ok(())
}

pub async fn leave_crew(client: &Client, user_id: i64) -> Result<(), String> {
    let crew = get_crew_by_member(client, user_id).await?;
    if let Some((crew_id, _, captain_id)) = crew {
        if captain_id == user_id {
            return Err("You are the captain! You must disband the crew instead.".to_string());
        }

        let stmt = client
            .prepare("DELETE FROM pirate_crew_members WHERE crew_id = $1 AND user_id = $2")
            .await.map_err(|e| e.to_string())?;
        client.execute(&stmt, &[&crew_id, &user_id]).await.map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("You are not in a crew!".to_string())
    }
}

pub async fn disband_crew(client: &Client, user_id: i64) -> Result<(), String> {
    let crew = get_crew_by_member(client, user_id).await?;
    if let Some((crew_id, _, captain_id)) = crew {
        if captain_id != user_id {
            return Err("Only the captain can disband the crew!".to_string());
        }

        let stmt = client
            .prepare("DELETE FROM pirate_crews WHERE id = $1")
            .await.map_err(|e| e.to_string())?;
        client.execute(&stmt, &[&crew_id]).await.map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("You are not in a crew!".to_string())
    }
}

pub async fn add_quiz_question(client: &Client, question: &str, answer: &str) -> Result<(), String> {
    let stmt = client
        .prepare("INSERT INTO quiz_questions (category, question, answer, options) VALUES ('one_piece', $1, $2, '[]')")
        .await.map_err(|e| e.to_string())?;

    client.execute(&stmt, &[&question, &answer]).await.map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn get_random_quiz(client: &Client) -> Result<Option<(i32, String, String)>, String> {
    let stmt = client
        .prepare("SELECT id, question, answer FROM quiz_questions ORDER BY RANDOM() LIMIT 1")
        .await.map_err(|e| e.to_string())?;

    let row_opt = client.query_opt(&stmt, &[]).await.map_err(|e| e.to_string())?;

    if let Some(row) = row_opt {
        Ok(Some((row.get(0), row.get(1), row.get(2))))
    } else {
        Ok(None)
    }
}

use crate::auth::{extract_target_user, resolve_username};
use crate::db::game_cooldown::list_cooldowns;
use crate::db::game_stats::{get_game_stats, get_game_stats_breakdown, get_user_game_history};
use crate::db::games::get_bounty;
use crate::db::leaderboard::{
    get_crew_leaderboard_detailed, get_crew_stats, get_user_leaderboard_detailed,
    reset_all_bounties,
};
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use crate::telegram::ParseMode;
use tokio_postgres::Client;

const BOARD_LIMIT: i64 = 10;

fn format_bounty(n: i64) -> String {
    let digits = n.abs().to_string();
    let neg = n < 0;
    let mut out = String::new();
    for (i, c) in digits.chars().enumerate() {
        if i > 0 && (digits.len() - i).is_multiple_of(3) {
            out.push(',');
        }
        out.push(c);
    }
    if neg {
        format!("-{}", out)
    } else {
        out
    }
}

fn medal(i: usize) -> &'static str {
    match i {
        0 => "🥇",
        1 => "🥈",
        2 => "🥉",
        _ => "▫️",
    }
}

/// 📊 /mystats — personal game statistics.
pub async fn handle_mystats(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    if user_id == 0 {
        return Ok(());
    }

    let bounty = get_bounty(client, user_id).await.unwrap_or(0);
    let (plays, wins) = get_game_stats(client, user_id).await.unwrap_or((0, 0));
    let crew = crate::db::games::get_crew_by_member(client, user_id)
        .await
        .unwrap_or(None);

    let mut text = format!(
        "📊 <b>Pirate Statistics</b>\n✿ ∘ ━━━━━━━━━┉┅╍\n\n\
         💰 Bounty: <b>{}</b> Berries\n\
         🎮 Voyages &amp; Quizzes played: <b>{}</b>\n\
         ⚔️ Wins: <b>{}</b>\n\
         🏴‍☠️ Crew: <b>{}</b>",
        format_bounty(bounty),
        plays,
        wins,
        crate::utils::escape_html(
            crew.as_ref()
                .map(|(_, name, _)| name)
                .unwrap_or(&"Solo Pirate".to_string())
        )
    );

    let breakdown = get_game_stats_breakdown(client, user_id)
        .await
        .unwrap_or_default();
    if !breakdown.is_empty() {
        text.push_str("\n\n📜 <b>Game History</b>");
        for s in &breakdown {
            text.push_str(&format!(
                "\n   • {} — {} plays, {} wins",
                crate::utils::escape_html(&s.game_type),
                s.plays,
                s.wins
            ));
        }
    }

    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(ParseMode::Html)
        .await;
    Ok(())
}

/// 🏴‍☠️ /crewboard — crew leaderboard with detailed stats.
pub async fn handle_crewboard(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match get_crew_leaderboard_detailed(client, BOARD_LIMIT).await {
        Ok(rankings) if rankings.is_empty() => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "No crew has yet earned a bounty, dear. Found your own with /crew create and write your name in history!",
                )
                .await;
        }
        Ok(rankings) => {
            let mut text = String::from("🏴‍☠️ <b>CREW LEADERBOARD</b> 🏴‍☠️\n✿ ∘ ━━━━━━━━━┉┅╍\n");
            for (i, crew) in rankings.iter().enumerate() {
                text.push_str(&format!(
                    "\n{} <b>{}</b> (Capt. {})\n   💰 {} Berries | 👥 {} | ⚡ {} avg\n   🌊 Voyages: {}",
                    medal(i),
                    crate::utils::escape_html(&crew.crew_name),
                    crate::utils::escape_html(&crew.captain_name),
                    format_bounty(crew.total_bounty),
                    crew.member_count,
                    format_bounty(crew.avg_bounty_per_member),
                    crew.total_voyages
                ));
            }
            text.push_str("\n\n✿ The World Government has taken notice... Fufufu.");
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(ParseMode::Html)
                .await;
        }
        Err(e) => {
            tracing::error!("Error fetching crew leaderboard: {}", e);
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "I couldn't chart the crew leaderboard right now.",
                )
                .await;
        }
    }
    Ok(())
}

/// 🏆 /toppirates — user leaderboard with crew affiliation.
pub async fn handle_toppirates(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match get_user_leaderboard_detailed(client, BOARD_LIMIT).await {
        Ok(rows) if rows.is_empty() => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "No pirate has yet earned a bounty, dear. Use /daily to begin your tale in the Wanted Ledger!",
                )
                .await;
        }
        Ok(rows) => {
            let mut text = String::from(
                "WALL OF WANTED POSTERS 🍁\nThe World's Most Notorious 🏴‍☠\n✿ ∘ ━━━━━━━━━┉┅╍\n",
            );
            for (i, row) in rows.iter().enumerate() {
                let formatted_name =
                    format!("<b>{}</b>", crate::utils::escape_html(&row.username));
                text.push_str(&format!(
                    "\n{} {}\n   💰 {} Berries\n   🏴‍☠️ {}",
                    medal(i),
                    formatted_name,
                    format_bounty(row.bounty),
                    crate::utils::escape_html(&row.crew_name)
                ));
            }
            text.push_str("\n\n✿ The World Government has taken notice... Fufufu.");
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(ParseMode::Html)
                .await;
        }
        Err(e) => {
            tracing::error!("Error fetching user leaderboard: {}", e);
            let _ = bot
                .send_message(msg.chat.id, "I couldn't chart the leaderboard right now.")
                .await;
        }
    }
    Ok(())
}

/// ⏳ /cooldown [game] — show remaining cooldowns for the current user.
pub async fn handle_cooldown(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    if user_id == 0 {
        return Ok(());
    }

    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    let requested = parts.get(1).map(|s| s.to_lowercase());

    let cooldowns = list_cooldowns(client, user_id).await.unwrap_or_default();

    let filtered: Vec<&(String, i32)> = match requested.as_deref() {
        Some(game) => cooldowns.iter().filter(|(g, _)| g == game).collect(),
        None => cooldowns.iter().collect(),
    };

    if filtered.is_empty() {
        let _ = bot
            .send_message(
                msg.chat.id,
                "🌊 The seas are clear — you have no active cooldowns, dear pirate. /voyage whenever you are ready.",
            )
            .await;
        return Ok(());
    }

    let mut text = String::from("⏳ <b>Active Cooldowns</b>\n✿ ∘ ━━━━━━━━━┉┅╍\n");
    for (game, remaining) in filtered {
        text.push_str(&format!(
            "\n⚓ <b>{}</b> — {}",
            crate::utils::escape_html(game),
            format_remaining(*remaining)
        ));
    }
    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(ParseMode::Html)
        .await;
    Ok(())
}

/// 🏴‍☠️ /crewstats — aggregate stats for the user's own crew.
pub async fn handle_crewstats(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    if user_id == 0 {
        return Ok(());
    }

    let crew = match crate::db::games::get_crew_by_member(client, user_id).await {
        Ok(Some(crew)) => crew,
        _ => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "You sail alone, dear pirate. Join a crew with /crew create or /crew join to see its statistics.",
                )
                .await;
            return Ok(());
        }
    };

    match get_crew_stats(client, crew.0).await {
        Ok(Some(stats)) => {
            let text = format!(
                "🏴‍☠️ <b>{}</b> (Rank #{})\n✿ ∘ ━━━━━━━━━┉┅╍\n\n\
                 ⚓ Captain: {}\n\
                 💰 Total Bounty: <b>{}</b> Berries\n\
                 👥 Members: {}\n\
                 ⚡ Average Bounty: {} per pirate\n\
                 🌊 Crew Voyages: {}\n\n\
                 The ledger remembers every wave your crew has crossed.",
                crate::utils::escape_html(&stats.crew_name),
                stats.rank,
                crate::utils::escape_html(&stats.captain_name),
                format_bounty(stats.total_bounty),
                stats.member_count,
                format_bounty(stats.avg_bounty_per_member),
                stats.total_voyages
            );
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(ParseMode::Html)
                .await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "I could not find statistics for your crew yet.",
                )
                .await;
        }
        Err(e) => {
            tracing::error!("Error fetching crew stats: {}", e);
            let _ = bot
                .send_message(msg.chat.id, "I couldn't read your crew's ledger right now.")
                .await;
        }
    }
    Ok(())
}

/// 🔄 /resetcooldown [@user] [game] — admin removes a user's game cooldown.
pub async fn handle_resetcooldown(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let mut target_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    let mut target_name = msg
        .from()
        .map(|u| u.first_name.clone())
        .unwrap_or_else(|| "you".to_string());

    if let Some((id, name)) = extract_target_user(&msg) {
        if id > 0 {
            target_id = id;
            target_name = name;
        } else {
            // @username — try to resolve in the current chat
            match resolve_username(&bot, msg.chat.id, &name).await {
                Some((id, name)) => {
                    target_id = id;
                    target_name = name;
                }
                None => {
                    let _ = bot
                        .send_message(
                            msg.chat.id,
                            "I couldn't resolve that username to a pirate in this chat.",
                        )
                        .await;
                    return Ok(());
                }
            }
        }
    }

    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    let mut game: Option<&str> = None;
    for part in parts.iter().skip(1) {
        if part.starts_with('@') {
            continue;
        }
        game = Some(part);
        break;
    }

    match game {
        Some(game) => {
            let removed = crate::db::game_cooldown::reset_cooldown(client, target_id, game).await?;
            let _ = bot
                .send_message(
                    msg.chat.id,
                    if removed {
                        format!(
                            "⚓ The cooldown on <b>{}</b> has been lifted for {}.",
                            crate::utils::escape_html(game),
                            crate::utils::escape_html(&target_name)
                        )
                    } else {
                        format!(
                            "{} had no active <b>{}</b> cooldown, dear.",
                            crate::utils::escape_html(&target_name),
                            crate::utils::escape_html(game)
                        )
                    },
                )
                .parse_mode(ParseMode::Html)
                .await;
        }
        None => {
            let removed =
                crate::db::game_cooldown::reset_cooldown(client, target_id, "voyage").await?;
            let _ = bot
                .send_message(
                    msg.chat.id,
                    if removed {
                        format!(
                            "⚓ All voyage cooldowns have been lifted for {}.",
                            crate::utils::escape_html(&target_name)
                        )
                    } else {
                        format!(
                            "{} had no active cooldowns, dear.",
                            crate::utils::escape_html(&target_name)
                        )
                    },
                )
                .parse_mode(ParseMode::Html)
                .await;
        }
    }

    Ok(())
}

/// 📜 /gamestats [@user] — admin views a user's detailed game history.
pub async fn handle_gamestats(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let mut target_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    let mut target_name = msg
        .from()
        .map(|u| u.first_name.clone())
        .unwrap_or_else(|| "this pirate".to_string());

    if let Some((id, name)) = extract_target_user(&msg) {
        if id > 0 {
            target_id = id;
            target_name = name;
        } else {
            match resolve_username(&bot, msg.chat.id, &name).await {
                Some((id, name)) => {
                    target_id = id;
                    target_name = name;
                }
                None => {
                    let _ = bot
                        .send_message(
                            msg.chat.id,
                            "I couldn't resolve that username to a pirate in this chat.",
                        )
                        .await;
                    return Ok(());
                }
            }
        }
    }

    let bounty = get_bounty(client, target_id).await.unwrap_or(0);
    let history = get_user_game_history(client, target_id)
        .await
        .unwrap_or_default();

    let mut text = format!(
        "📜 <b>Game Audit — {}</b>\n✿ ∘ ━━━━━━━━━┉┅╍\n\n💰 Bounty: <b>{}</b> Berries",
        crate::utils::escape_html(&target_name),
        format_bounty(bounty)
    );

    if history.is_empty() {
        text.push_str("\n\nNo games played yet.");
    } else {
        text.push_str("\n\n🎮 <b>History</b>");
        for (game, plays, wins, rate) in &history {
            text.push_str(&format!(
                "\n   • {} — {} plays, {} wins ({}%)",
                crate::utils::escape_html(game),
                plays,
                wins,
                rate
            ));
        }
    }

    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(ParseMode::Html)
        .await;
    Ok(())
}

/// 🗑 /leaderboard reset [confirm] — admin wipes the Wanted Ledger.
pub async fn handle_leaderboard_reset(
    bot: Bot,
    msg: Message,
    client: &Client,
) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    let confirmed = parts.iter().any(|p| p.eq_ignore_ascii_case("confirm"));

    if !confirmed {
        let _ = bot
            .send_message(
                msg.chat.id,
                "⚠️ This will <b>permanently erase every pirate's bounty</b> and restart the game.\n\
                 Send <code>/leaderboard reset confirm</code> to proceed.",
            )
            .parse_mode(ParseMode::Html)
            .await;
        return Ok(());
    }

    match reset_all_bounties(client).await {
        Ok(cleared) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!(
                        "🌊 The Wanted Ledger has been wiped clean — {} pirate records erased.\n\nA new era of the Grand Line begins... Fufufu.",
                        cleared
                    ),
                )
                .await;
        }
        Err(e) => {
            tracing::error!("Error resetting leaderboard: {}", e);
            let _ = bot
                .send_message(msg.chat.id, "I couldn't erase the ledger right now.")
                .await;
        }
    }
    Ok(())
}

fn format_remaining(secs: i32) -> String {
    let h = secs / 3600;
    let m = (secs % 3600) / 60;
    if h > 0 {
        format!("{}h {}m remaining", h, m)
    } else if m > 0 {
        format!("{}m remaining", m)
    } else {
        format!("{}s remaining", secs)
    }
}

use crate::db::games::{claim_daily_bounty, get_bounty, get_leaderboard};
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

const LEADERBOARD_LIMIT: i64 = 10;

pub async fn handle_bounty(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    let bounty = get_bounty(client, user_id as i64).await.unwrap_or(0);
    let text = format!(
        "Fufufu... Let me consult the <b>Wanted Ledger</b>, dear pirate.\nYour bounty stands at <b>{} Berries</b>.",
        bounty
    );
    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(crate::telegram::ParseMode::Html)
        .await;

    Ok(())
}

pub async fn handle_leaderboard(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match get_leaderboard(client, LEADERBOARD_LIMIT).await {
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
                "WALL OF WANTED POSTERS 🍁\nThe World's Most Notorious 🏴‍☠\n✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            );
            for (i, (user_id, bounty, name)) in rows.iter().enumerate() {
                let medal = match i {
                    0 => "🥇",
                    1 => "🥈",
                    2 => "🥉",
                    _ => "▫️",
                };

                let escaped_name = crate::utils::escape_html(name);
                let formatted_name = match i {
                    0 => format!("🌹{}", escaped_name), // 1st place: add rose
                    1 => format!("<b>{}</b>", escaped_name), // 2nd place: bold
                    _ => escaped_name, // 3rd place and beyond: normal
                };

                text.push_str(&format!(
                    "\n{} {} - 💰 {} Berries",
                    medal, formatted_name, bounty
                ));
            }
            text.push_str("\n\n✿ ∘ ━━━━━━━━━━┉┅╍\nThe World Government has taken notice... Fufufu.");
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        Err(e) => {
            tracing::error!("Error fetching leaderboard: {}", e);
            let _ = bot
                .send_message(msg.chat.id, "I couldn't chart the leaderboard right now.")
                .await;
        }
    }

    Ok(())
}

pub async fn handle_daily(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    match claim_daily_bounty(client, user_id as i64).await {
        Ok(Ok(new_bounty)) => {
            let text = format!(
                "📅 The <b>Log Pose</b> has realigned, dear pirate. +5 Berries claimed.\nYour total bounty is now <b>{} Berries</b>.",
                new_bounty
            );
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        Ok(Err(err_msg)) => {
            let _ = bot.send_message(msg.chat.id, err_msg).await;
        }
        Err(e) => {
            tracing::error!("Error claiming daily bounty: {}", e);
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "I'm sorry, the tides are against us — I couldn't process your daily bounty right now.",
                )
                .await;
        }
    }

    Ok(())
}

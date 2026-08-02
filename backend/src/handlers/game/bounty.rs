use crate::db::games::{claim_daily_bounty, get_bounty};
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

pub async fn handle_bounty(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    let bounty = get_bounty(client, user_id as i64).await.unwrap_or(0);
    let text = format!("Fufufu... Your current bounty is {} Berries.", bounty);
    let _ = bot
        .send_message(msg.chat.id, crate::utils::escape_md_v2(&text))
        .await;

    Ok(())
}

pub async fn handle_daily(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    match claim_daily_bounty(client, user_id as i64).await {
        Ok(Ok(new_bounty)) => {
            let text = format!("Here is your daily allowance, pirate. +5 Berries!\nYour total bounty is now {} Berries.", new_bounty);
            let _ = bot
                .send_message(msg.chat.id, crate::utils::escape_md_v2(&text))
                .await;
        }
        Ok(Err(err_msg)) => {
            let _ = bot
                .send_message(msg.chat.id, crate::utils::escape_md_v2(&err_msg))
                .await;
        }
        Err(e) => {
            tracing::error!("Error claiming daily bounty: {}", e);
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "I'm sorry, I couldn't process your daily bounty at this time.",
                )
                .await;
        }
    }

    Ok(())
}

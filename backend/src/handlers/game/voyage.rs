use crate::db::games::perform_voyage;
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

pub async fn handle_voyage(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    match perform_voyage(client, user_id as i64).await {
        Ok(Ok((change, new_bounty, msg_text))) => {
            let sign = if change > 0 { "+" } else { "" };
            let text = format!(
                "🌊 The <b>Grand Line Voyage</b> begins, dear pirate...\n\n{}\n\nYour voyage result: {}{} Berries\n\nYour new bounty is <b>{} Berries</b>.\nFufufu... the sea has written another verse of your tale.",
                msg_text, sign, change, new_bounty
            );
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        Ok(Err(err_msg)) => {
            let text = format!("Fufufu... {}", err_msg);
            let _ = bot.send_message(msg.chat.id, text).await;
        }
        Err(e) => {
            tracing::error!("Error performing voyage: {}", e);
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "The Log Pose is spinning wildly — I couldn't chart a course for your voyage.",
                )
                .await;
        }
    }

    Ok(())
}

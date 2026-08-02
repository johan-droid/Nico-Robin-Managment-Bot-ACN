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
            let text = format!("The seas are unpredictable...\n\n{}\n\nYour voyage result: *{}{}* Berries\n\nYour new bounty is *{}* Berries.", msg_text, sign, change, new_bounty);
            let _ = bot
                .send_message(msg.chat.id, crate::utils::escape_md_v2(&text))
                .await;
        }
        Ok(Err(err_msg)) => {
            let text = format!("Fufufu... {}", err_msg);
            let _ = bot
                .send_message(msg.chat.id, crate::utils::escape_md_v2(&text))
                .await;
        }
        Err(e) => {
            tracing::error!("Error performing voyage: {}", e);
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "I couldn't chart a course for your voyage right now.",
                )
                .await;
        }
    }

    Ok(())
}

use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

async fn send_text(bot: &Bot, chat_id: i64, text: &str) {
    let _ = bot.send_or_edit(chat_id, text, None, None).await;
}

/// /purge — reply to a message to delete it and everything after it.
/// /purge <n> — delete the last n messages in the group.
pub async fn handle_purge(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("").trim();
    let arg = text.strip_prefix("/purge").unwrap_or("").trim();

    let chat_id = msg.chat.id;
    let ids: Vec<u64> = if let Some(reply) = msg.reply_to_message() {
        // Delete the replied message up to (but not including) the command message.
        crate::db::message_history::get_recent_between(client, chat_id, reply.id(), msg.id())
            .await
            .unwrap_or_default()
            .into_iter()
            .map(|m| m.message_id)
            .collect()
    } else if !arg.is_empty() {
        // Delete the last n messages in the chat.
        let n: usize = match arg.parse::<usize>() {
            Ok(v) => v.min(100),
            Err(_) => {
                send_text(&bot, chat_id, "Usage: /purge <count> or reply to a message to purge from there.").await;
                return Ok(());
            }
        };
        crate::db::message_history::get_recent(client, chat_id, n)
            .await
            .unwrap_or_default()
            .into_iter()
            .map(|m| m.message_id)
            .collect()
    } else {
        send_text(&bot, chat_id, "Usage: /purge <count> or reply to a message to purge from there.").await;
        return Ok(());
    };

    // Include the command message itself.
    let mut to_delete = ids;
    if !to_delete.iter().any(|&id| id == msg.id()) {
        to_delete.push(msg.id());
    }
    to_delete.sort_unstable();
    to_delete.dedup();

    let count = to_delete.len();
    if count == 0 {
        send_text(&bot, chat_id, "No messages found to purge.").await;
        return Ok(());
    }

    match bot.delete_messages(chat_id, to_delete).await {
        Ok(_) => {
            let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
            send_text(&bot, chat_id, &format!("Purged {} messages 🧹", count)).await;
            log_mod_action(
                &bot,
                crate::config::Settings::global(),
                chat_id,
                &format!(
                    "Purged {} messages in {} (by {})",
                    count,
                    escape_md_v2(msg.chat.title().unwrap_or("group")),
                    escape_md_v2(executor)
                ),
            )
            .await;
        }
        Err(e) => send_text(&bot, chat_id, &format!("Failed to purge: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

use crate::telegram::api::Bot;
use crate::telegram::ParseMode;
use crate::telegram::update::Message;
use tokio_postgres::Client;

use crate::utils::escape_md_v2;

pub async fn handle_filter(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.splitn(3, ' ').collect();
    if parts.len() < 3 {
        bot.reply_or_edit(msg.chat.id, "Usage: /filter <trigger> <response>")
            .await?;
        return Ok(());
    }
    let trigger = parts[1];
    let response = parts[2];
    let user_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    let chat_id = msg.chat.id;

    match crate::db::filters::add_filter(client, chat_id, trigger, response, user_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!(
                        "Filter set: '{}' -> '{}'",
                        escape_md_v2(trigger),
                        escape_md_v2(response)
                    ),
                )
                .await;
        }
        Err(e) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Error: {}", escape_md_v2(&e.to_string())),
                )
                .await;
        }
    }
    Ok(())
}

pub async fn handle_stop(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.reply_or_edit(msg.chat.id, "Usage: /stop <trigger>")
            .await?;
        return Ok(());
    }
    let trigger = parts[1];
    let chat_id = msg.chat.id;

    match crate::db::filters::remove_filter(client, chat_id, trigger).await {
        Ok(true) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Filter '{}' removed.", escape_md_v2(trigger)),
                )
                .await;
        }
        Ok(false) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Filter '{}' not found.", escape_md_v2(trigger)),
                )
                .await;
        }
        Err(e) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Error: {}", escape_md_v2(&e.to_string())),
                )
                .await;
        }
    }
    Ok(())
}

pub async fn handle_filters_list(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::filters::list_filters(client, chat_id).await {
        Ok(filters) => {
            if filters.is_empty() {
                let _ = bot.reply_or_edit(msg.chat.id, "No filters set.").await;
            } else {
                let mut text = String::from("*Filters:*\n");
                for f in &filters {
                    text.push_str(&format!(
                        "`{}` \\-\\> {}\n",
                        escape_md_v2(&f.trigger_text),
                        escape_md_v2(&f.response)
                    ));
                }
                let _ = bot
                    .send_message(msg.chat.id, text)
                    .parse_mode(ParseMode::MarkdownV2)
                    .await;
            }
        }
        Err(e) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Error: {}", escape_md_v2(&e.to_string())),
                )
                .await;
        }
    }
    Ok(())
}

use sqlx::PgPool;
use teloxide::prelude::*;

use crate::handlers::FilterCache;
use crate::utils::escape_md_v2;

pub async fn handle_filter(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
    cache: &FilterCache,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.splitn(3, ' ').collect();
    if parts.len() < 3 {
        bot.send_message(msg.chat.id, "Usage: /filter <trigger> <response>")
            .await?;
        return Ok(());
    }
    let trigger = parts[1];
    let response = parts[2];
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let chat_id = msg.chat.id.0 as i64;

    match crate::db::filters::add_filter(pool, chat_id, trigger, response, user_id).await {
        Ok(_) => {
            cache
                .write()
                .await
                .entry(chat_id)
                .or_default()
                .insert(trigger.to_string(), response.to_string());
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Filter set: '{}' -> '{}'", escape_md_v2(trigger), escape_md_v2(response)),
                )
                .await;
        }
        Err(e) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Error: {}", escape_md_v2(&e.to_string())))
                .await;
        }
    }
    Ok(())
}

pub async fn handle_stop(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
    cache: &FilterCache,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.send_message(msg.chat.id, "Usage: /stop <trigger>")
            .await?;
        return Ok(());
    }
    let trigger = parts[1];
    let chat_id = msg.chat.id.0 as i64;

    match crate::db::filters::remove_filter(pool, chat_id, trigger).await {
        Ok(true) => {
            if let Some(group_filters) = cache.write().await.get_mut(&chat_id) {
                group_filters.remove(trigger);
            }
            let _ = bot
                .send_message(msg.chat.id, format!("Filter '{}' removed.", escape_md_v2(trigger)))
                .await;
        }
        Ok(false) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Filter '{}' not found.", escape_md_v2(trigger)))
                .await;
        }
        Err(e) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Error: {}", escape_md_v2(&e.to_string())))
                .await;
        }
    }
    Ok(())
}

pub async fn handle_filters_list(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::filters::list_filters(pool, chat_id).await {
        Ok(filters) => {
            if filters.is_empty() {
                let _ = bot
                    .send_message(msg.chat.id, "No filters set.")
                    .await;
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
                    .parse_mode(teloxide::types::ParseMode::MarkdownV2)
                    .await;
            }
        }
        Err(e) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Error: {}", escape_md_v2(&e.to_string())))
                .await;
        }
    }
    Ok(())
}

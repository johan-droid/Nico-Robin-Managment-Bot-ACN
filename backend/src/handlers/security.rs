use sqlx::PgPool;
use teloxide::prelude::*;

use crate::handlers::SwearCache;
use crate::utils::escape_md_v2;

pub async fn handle_setflood(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.send_message(
            msg.chat.id,
            "Usage: /setflood <count>\nSets the max messages per user in a 10-second window.\nUse 0 to disable.",
        )
        .await?;
        return Ok(());
    }
    let count: i32 = match parts[1].parse() {
        Ok(v) => v,
        Err(_) => {
            bot.send_message(msg.chat.id, "Invalid number.").await?;
            return Ok(());
        }
    };
    let chat_id = msg.chat.id.0 as i64;
    let mode = if count == 0 { "off" } else { "warn" };
    let window = 10;

    match crate::db::flood::set_flood_settings(pool, chat_id, count, mode, window).await {
        Ok(_) => {
            if count == 0 {
                let _ = bot.send_message(msg.chat.id, "Flood protection disabled.").await;
            } else {
                let _ = bot.send_message(
                    msg.chat.id,
                    format!("Flood limit set to {} messages per {} seconds.", count, window),
                ).await;
            }
        }
        Err(e) => {
            let _ = bot.send_message(msg.chat.id, format!("Error: {}", escape_md_v2(&e.to_string()))).await;
        }
    }
    Ok(())
}

pub async fn handle_flood(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::flood::get_flood_settings(pool, chat_id).await {
        Ok(Some((limit, mode, window))) => {
            let _ = bot.send_message(
                msg.chat.id,
                format!("Flood settings:\nLimit: {} messages per {} seconds\nMode: {}", limit, window, mode),
            ).await;
        }
        Ok(None) => {
            let _ = bot.send_message(
                msg.chat.id,
                "No flood settings configured. Use /setflood <count> to set one.",
            ).await;
        }
        Err(e) => {
            let _ = bot.send_message(msg.chat.id, format!("Error: {}", escape_md_v2(&e.to_string()))).await;
        }
    }
    Ok(())
}

pub async fn handle_addswear(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
    cache: &SwearCache,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.send_message(msg.chat.id, "Usage: /addswear <word>")
            .await?;
        return Ok(());
    }
    let word = parts[1].to_lowercase();
    let chat_id = msg.chat.id.0 as i64;

    match crate::db::swears::add_swear(pool, chat_id, &word).await {
        Ok(_) => {
            let mut write = cache.write().await;
            let group_swears = write.entry(chat_id).or_default();
            if !group_swears.contains(&word) {
                group_swears.push(word.clone());
            }
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Swear word '{}' added.", escape_md_v2(&word)),
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

pub async fn handle_delswear(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
    cache: &SwearCache,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.send_message(msg.chat.id, "Usage: /delswear <word>")
            .await?;
        return Ok(());
    }
    let word = parts[1].to_lowercase();
    let chat_id = msg.chat.id.0 as i64;

    match crate::db::swears::remove_swear(pool, chat_id, &word).await {
        Ok(true) => {
            let mut write = cache.write().await;
            if let Some(group_swears) = write.get_mut(&chat_id) {
                group_swears.retain(|w| w != &word);
            }
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Swear word '{}' removed.", escape_md_v2(&word)),
                )
                .await;
        }
        Ok(false) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Swear word '{}' not found.", escape_md_v2(&word)),
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

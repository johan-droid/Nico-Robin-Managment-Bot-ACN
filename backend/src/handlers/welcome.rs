use sqlx::PgPool;
use teloxide::prelude::*;

use crate::utils::escape_md_v2;

pub async fn handle_setwelcome(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setwelcome ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(
            msg.chat.id,
            "Usage: /setwelcome <message>\nVariables: {user}, {group}, {count}",
        )
        .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::set_welcome_message(pool, chat_id, content).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Welcome message set.")
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

pub async fn handle_resetwelcome(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::reset_welcome_message(pool, chat_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Welcome message reset.")
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

pub async fn handle_welcome_preview(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::get_welcome_settings(pool, chat_id).await {
        Ok(Some(settings)) => {
            let welcome = settings
                .welcome_message
                .unwrap_or_else(|| "No welcome message set.".to_string());
            let _ = bot
                .send_message(msg.chat.id, &welcome)
                .await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(msg.chat.id, "No welcome message set.")
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

pub async fn handle_setwelcomedm(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setwelcomedm ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /setwelcomedm <message>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::set_welcome_dm_message(pool, chat_id, content).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Welcome DM message set.")
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

pub async fn handle_setfarewell(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setfarewell ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /setfarewell <message>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::set_farewell_message(pool, chat_id, content).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Farewell message set.")
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

pub async fn handle_farewell_preview(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::get_welcome_settings(pool, chat_id).await {
        Ok(Some(settings)) => {
            let farewell = settings
                .farewell_message
                .unwrap_or_else(|| "No farewell message set.".to_string());
            let _ = bot
                .send_message(msg.chat.id, &farewell)
                .await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(msg.chat.id, "No farewell message set.")
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

pub async fn handle_cleanwelcome(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::toggle_clean_welcome(pool, chat_id).await {
        Ok(enabled) => {
            let status = if enabled { "enabled" } else { "disabled" };
            let _ = bot
                .send_message(msg.chat.id, format!("Clean welcome {}.", status))
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

pub async fn handle_welcometest(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::welcome::get_welcome_settings(pool, chat_id).await {
        Ok(Some(settings)) => {
            let user_name = msg
                .from()
                .map(|u| u.first_name.as_str())
                .unwrap_or("User");
            let welcome = settings
                .welcome_message
                .unwrap_or_else(|| "Hello {user}!".to_string());
            let member_count = bot
                .get_chat_member_count(msg.chat.id)
                .await
                .map(|c| c.to_string())
                .unwrap_or_else(|_| "N/A".to_string());
            let welcome = welcome
                .replace("{user}", user_name)
                .replace("{group}", msg.chat.title().unwrap_or("this group"))
                .replace("{count}", &member_count);
            let _ = bot
                .send_message(msg.chat.id, &welcome)
                .await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(msg.chat.id, "No welcome message set. Use /setwelcome first.")
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

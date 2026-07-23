use sqlx::PgPool;
use teloxide::prelude::*;

use crate::utils::escape_md_v2;

pub async fn handle_save(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.splitn(3, ' ').collect();
    if parts.len() < 3 {
        bot.send_message(msg.chat.id, "Usage: /save <name> <content>")
            .await?;
        return Ok(());
    }
    let name = parts[1];
    let content = parts[2];
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let chat_id = msg.chat.id.0;

    match crate::db::notes::save_note(pool, chat_id, name, content, user_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Note '{}' saved.", escape_md_v2(name)))
                .await;
        }
        Err(e) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Failed to save note: {}", escape_md_v2(&e.to_string())),
                )
                .await;
        }
    }
    Ok(())
}

pub async fn handle_get(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.send_message(msg.chat.id, "Usage: /get <name>").await?;
        return Ok(());
    }
    let name = parts[1];
    let chat_id = msg.chat.id.0;

    match crate::db::notes::get_note(pool, chat_id, name).await {
        Ok(Some(content)) => {
            let _ = bot.send_message(msg.chat.id, &content).await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Note '{}' not found.", escape_md_v2(name)),
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

pub async fn handle_notes(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0;
    match crate::db::notes::list_notes(pool, chat_id).await {
        Ok(notes) => {
            if notes.is_empty() {
                let _ = bot.send_message(msg.chat.id, "No notes saved yet.").await;
            } else {
                let list = notes.join(", ");
                let _ = bot
                    .send_message(msg.chat.id, format!("Notes: {}", list))
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

pub async fn handle_clear(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        bot.send_message(msg.chat.id, "Usage: /clear <name>")
            .await?;
        return Ok(());
    }
    let name = parts[1];
    let chat_id = msg.chat.id.0;

    match crate::db::notes::delete_note(pool, chat_id, name).await {
        Ok(true) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Note '{}' deleted.", escape_md_v2(name)),
                )
                .await;
        }
        Ok(false) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Note '{}' not found.", escape_md_v2(name)),
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

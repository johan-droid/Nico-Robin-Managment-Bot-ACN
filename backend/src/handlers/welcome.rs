use crate::telegram::api::Bot;
use crate::telegram::update::{Message, User};
use tokio_postgres::Client;

use crate::utils::escape_md_v2;

pub async fn handle_setwelcome(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
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
    let chat_id = msg.chat.id;
    match crate::db::welcome::set_welcome_message(client, chat_id, content).await {
        Ok(_) => {
            let _ = bot.send_message(msg.chat.id, "Welcome message set.").await;
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

pub async fn handle_resetwelcome(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::welcome::reset_welcome_message(client, chat_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Welcome message reset.")
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

pub async fn handle_welcome_preview(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::welcome::get_welcome_settings(client, chat_id).await {
        Ok(Some(settings)) => {
            let welcome = settings
                .welcome_message
                .unwrap_or_else(|| "No welcome message set.".to_string());
            let _ = bot.send_message(msg.chat.id, &welcome).await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(msg.chat.id, "No welcome message set.")
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

pub async fn handle_setwelcomedm(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setwelcomedm ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /setwelcomedm <message>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id;
    match crate::db::welcome::set_welcome_dm_message(client, chat_id, content).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Welcome DM message set.")
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

pub async fn handle_setfarewell(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setfarewell ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /setfarewell <message>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id;
    match crate::db::welcome::set_farewell_message(client, chat_id, content).await {
        Ok(_) => {
            let _ = bot.send_message(msg.chat.id, "Farewell message set.").await;
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

pub async fn handle_farewell_preview(
    bot: Bot,
    msg: Message,
    client: &Client,
) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::welcome::get_welcome_settings(client, chat_id).await {
        Ok(Some(settings)) => {
            let farewell = settings
                .farewell_message
                .unwrap_or_else(|| "No farewell message set.".to_string());
            let _ = bot.send_message(msg.chat.id, &farewell).await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(msg.chat.id, "No farewell message set.")
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

pub async fn handle_cleanwelcome(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::welcome::toggle_clean_welcome(client, chat_id).await {
        Ok(enabled) => {
            let status = if enabled { "enabled" } else { "disabled" };
            let _ = bot
                .send_message(msg.chat.id, format!("Clean welcome {}.", status))
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

/// Handles a new member joining the group — sends welcome message and DM.
pub async fn handle_new_member(
    bot: &Bot,
    msg: &Message,
    client: &Client,
    member: &User,
) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::welcome::get_welcome_settings(client, chat_id).await {
        Ok(Some(settings)) => {
            // Send welcome message to group
            if let Some(ref welcome) = settings.welcome_message {
                let member_count = bot
                    .get_chat_member_count(chat_id)
                    .await
                    .map(|c| c.to_string())
                    .unwrap_or_else(|_| "N/A".to_string());
                let text = welcome
                    .replace("{user}", &member.first_name)
                    .replace("{group}", msg.chat.title().unwrap_or("this group"))
                    .replace("{count}", &member_count);
                let sent = bot.send_message(chat_id, &text).await.ok();

                // If clean_welcome is enabled, delete the welcome message after 60 seconds
                if settings.clean_welcome {
                    if let Some(sent_msg) = sent {
                        let bot_clone = bot.clone();
                        let msg_id = sent_msg.id();
                        crate::utils::spawn_task(async move {
                            tokio::time::sleep(std::time::Duration::from_secs(60)).await;
                            let _ = bot_clone.delete_message(chat_id, msg_id).await;
                        });
                    }
                }
            }

            // Send DM to new member
            if let Some(ref dm) = settings.welcome_dm_message {
                let text = dm
                    .replace("{user}", &member.first_name)
                    .replace("{group}", msg.chat.title().unwrap_or("this group"));
                let _ = bot.send_message(member.id as i64, &text).await;
            }
        }
        Ok(None) => {}
        Err(e) => {
            tracing::error!("Error getting welcome settings: {}", e);
        }
    }
    Ok(())
}

/// Handles a member leaving the group — sends farewell message.
pub async fn handle_left_member(bot: &Bot, msg: &Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    if let Some(ref left_user) = msg.left_chat_member {
        match crate::db::welcome::get_welcome_settings(client, chat_id).await {
            Ok(Some(settings)) => {
                if let Some(ref farewell) = settings.farewell_message {
                    let text = farewell
                        .replace("{user}", &left_user.first_name)
                        .replace("{group}", msg.chat.title().unwrap_or("this group"));
                    let _ = bot.send_message(chat_id, &text).await;
                }
            }
            Ok(None) => {}
            Err(e) => {
                tracing::error!("Error getting farewell settings: {}", e);
            }
        }
    }
    Ok(())
}

pub async fn handle_welcometest(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    match crate::db::welcome::get_welcome_settings(client, chat_id).await {
        Ok(Some(settings)) => {
            let user_name = msg.from().map(|u| u.first_name.as_str()).unwrap_or("User");
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
            let _ = bot.send_message(msg.chat.id, &welcome).await;
        }
        Ok(None) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "No welcome message set. Use /setwelcome first.",
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

use sqlx::PgPool;
use teloxide::prelude::*;

use uuid::Uuid;

use crate::utils::escape_md_v2;

pub async fn handle_newfed(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let name = text.strip_prefix("/newfed ").unwrap_or("").trim();
    if name.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /newfed <federation name>")
            .await?;
        return Ok(());
    }
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let fed_id = Uuid::new_v4().to_string()[..8].to_string();

    match crate::db::federations::create_federation(pool, &fed_id, name, user_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!(
                        "Federation '{}' created\\!\nFederation ID: `{}`",
                        escape_md_v2(name),
                        escape_md_v2(&fed_id)
                    ),
                )
                .parse_mode(teloxide::types::ParseMode::MarkdownV2)
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

pub async fn handle_joinfed(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let fed_id = text.strip_prefix("/joinfed ").unwrap_or("").trim();
    if fed_id.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /joinfed <federation_id>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0;

    match crate::db::federations::federation_exists(pool, fed_id).await {
        Ok(true) => match crate::db::federations::join_federation(pool, fed_id, chat_id).await {
            Ok(true) => {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        format!("Group joined federation `{}`\\.", escape_md_v2(fed_id)),
                    )
                    .parse_mode(teloxide::types::ParseMode::MarkdownV2)
                    .await;
            }
            Ok(false) => {
                let _ = bot
                    .send_message(msg.chat.id, "Group is already in this federation.")
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
        },
        Ok(false) => {
            let _ = bot.send_message(msg.chat.id, "Federation not found.").await;
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

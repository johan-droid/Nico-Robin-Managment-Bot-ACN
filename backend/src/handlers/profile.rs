use sqlx::PgPool;
use teloxide::prelude::*;

use crate::auth::extract_target_user;
use crate::utils::escape_md_v2;

pub async fn handle_profile(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let target_id = match extract_target_user(&msg) {
        Some((id, _)) if id != 0 => id,
        _ => msg.from().map(|u| u.id.0 as i64).unwrap_or(0),
    };
    if target_id == 0 {
        bot.send_message(msg.chat.id, "Could not resolve user.")
            .await?;
        return Ok(());
    }
    match crate::db::profiles::get_or_create_profile(pool, target_id).await {
        Ok(profile) => {
            let text = format!(
                "*User Profile*\n\nUser ID: {}\nBio: {}\nData: {}",
                escape_md_v2(&profile.user_id.to_string()),
                escape_md_v2(if profile.bio.is_empty() { "Not set" } else { &profile.bio }),
                escape_md_v2(&profile.data.to_string())
            );
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(teloxide::types::ParseMode::MarkdownV2)
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

pub async fn handle_setbio(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setbio ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /setbio <your bio>")
            .await?;
        return Ok(());
    }
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    match crate::db::profiles::set_bio(pool, user_id, content).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, "Bio updated.")
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

pub async fn handle_export(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    match crate::db::profiles::get_or_create_profile(pool, user_id).await {
        Ok(profile) => {
            let data = serde_json::json!({
                "user_id": profile.user_id,
                "bio": profile.bio,
                "data": profile.data
            });
            let json_str = serde_json::to_string_pretty(&data).unwrap_or_default();
            let text = format!("*Your Data:*\n```\n{}\n```", escape_md_v2(&json_str));
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(teloxide::types::ParseMode::MarkdownV2)
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

pub async fn handle_delete_data(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    match crate::db::profiles::delete_profile(pool, user_id).await {
        Ok(true) => {
            let _ = bot
                .send_message(msg.chat.id, "Your data has been deleted.")
                .await;
        }
        Ok(false) => {
            let _ = bot
                .send_message(msg.chat.id, "No data found to delete.")
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

use sqlx::PgPool;
use teloxide::prelude::*;

use crate::utils::escape_md_v2;

const FEATURE_CATEGORIES: &[(&str, &[&str])] = &[
    ("moderation", &["ban", "kick", "mute", "warn", "slowmode"]),
    ("notes", &["save", "get", "notes", "clear"]),
    ("filters", &["filter", "stop", "filters"]),
    ("welcome", &["welcome", "farewell"]),
    ("security", &["flood", "swear"]),
    ("profile", &["profile", "setbio"]),
    ("federation", &["newfed", "joinfed"]),
];

pub async fn handle_features_list(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::features::list_features(pool, chat_id).await {
        Ok(features) => {
            if features.is_empty() {
                let _ = bot
                    .send_message(msg.chat.id, "All features are at default (enabled).")
                    .await;
            } else {
                let mut text = String::from("*Features:*\n");
                for (name, enabled) in &features {
                    let status = if *enabled { "ON" } else { "OFF" };
                    text.push_str(&format!("{} {}\n", status, escape_md_v2(name)));
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

pub async fn handle_enable(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let name = text.strip_prefix("/enable ").unwrap_or("").trim();
    if name.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /enable <feature_name>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0 as i64;
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);

    match crate::db::features::enable_feature(pool, chat_id, name, user_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Feature '{}' enabled.", escape_md_v2(name)))
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

pub async fn handle_disable(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let name = text.strip_prefix("/disable ").unwrap_or("").trim();
    if name.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /disable <feature_name>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0 as i64;
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);

    match crate::db::features::disable_feature(pool, chat_id, name, user_id).await {
        Ok(_) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Feature '{}' disabled.", escape_md_v2(name)))
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

pub async fn handle_toggle(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let name = text.strip_prefix("/toggle ").unwrap_or("").trim();
    if name.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /toggle <feature_name>")
            .await?;
        return Ok(());
    }
    let chat_id = msg.chat.id.0 as i64;
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);

    let current = crate::db::features::is_feature_enabled(pool, chat_id, name)
        .await
        .unwrap_or(true);
    if current {
        let _ = crate::db::features::disable_feature(pool, chat_id, name, user_id).await;
        let _ = bot
            .send_message(msg.chat.id, format!("Feature '{}' disabled.", escape_md_v2(name)))
            .await;
    } else {
        let _ = crate::db::features::enable_feature(pool, chat_id, name, user_id).await;
        let _ = bot
            .send_message(msg.chat.id, format!("Feature '{}' enabled.", escape_md_v2(name)))
            .await;
    }
    Ok(())
}

pub async fn handle_feature_info(
    bot: Bot,
    msg: Message,
) -> Result<(), teloxide::RequestError> {
    let mut text = String::from("*Feature Categories:*\n\n");
    for (category, features) in FEATURE_CATEGORIES {
        text.push_str(&format!(
            "*{}* — {}\n",
            escape_md_v2(category),
            escape_md_v2(&features.join(", "))
        ));
    }
    text.push_str("\nUse /enablecategory or /disablecategory to toggle entire categories\\.");
    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(teloxide::types::ParseMode::MarkdownV2)
        .await;
    Ok(())
}

pub async fn handle_my_features(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::features::list_features(pool, chat_id).await {
        Ok(features) => {
            let enabled_count = features.iter().filter(|(_, e)| *e).count();
            let disabled_count = features.len() - enabled_count;
            let text = format!(
                "Your group features:\nEnabled: {}\nDisabled: {}\nTotal overrides: {}",
                enabled_count, disabled_count, features.len()
            );
            let _ = bot.send_message(msg.chat.id, text).await;
        }
        Err(e) => {
            let _ = bot
                .send_message(msg.chat.id, format!("Error: {}", escape_md_v2(&e.to_string())))
                .await;
        }
    }
    Ok(())
}

pub async fn handle_reset_features(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match crate::db::features::reset_features(pool, chat_id).await {
        Ok(count) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Reset {} feature overrides.", count),
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

pub async fn handle_enable_category(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let category = text.strip_prefix("/enable_category ").unwrap_or("").trim();
    if category.is_empty() {
        let cats: Vec<&str> = FEATURE_CATEGORIES.iter().map(|(c, _)| *c).collect();
        let _ = bot
            .send_message(
                msg.chat.id,
                format!("Usage: /enable_category <category>\nAvailable: {}", cats.join(", ")),
            )
            .await;
        return Ok(());
    }

    let features = FEATURE_CATEGORIES
        .iter()
        .find(|(c, _)| *c == category)
        .map(|(_, f)| *f);

    match features {
        Some(feats) => {
            let chat_id = msg.chat.id.0 as i64;
            let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
            for feat in feats {
                let _ = crate::db::features::enable_feature(pool, chat_id, feat, user_id).await;
            }
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Category '{}' enabled ({} features).", escape_md_v2(category), feats.len()),
                )
                .await;
        }
        None => {
            let _ = bot
                .send_message(msg.chat.id, "Category not found.")
                .await;
        }
    }
    Ok(())
}

pub async fn handle_disable_category(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let category = text.strip_prefix("/disable_category ").unwrap_or("").trim();
    if category.is_empty() {
        let cats: Vec<&str> = FEATURE_CATEGORIES.iter().map(|(c, _)| *c).collect();
        let _ = bot
            .send_message(
                msg.chat.id,
                format!("Usage: /disable_category <category>\nAvailable: {}", cats.join(", ")),
            )
            .await;
        return Ok(());
    }

    let features = FEATURE_CATEGORIES
        .iter()
        .find(|(c, _)| *c == category)
        .map(|(_, f)| *f);

    match features {
        Some(feats) => {
            let chat_id = msg.chat.id.0 as i64;
            let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
            for feat in feats {
                let _ = crate::db::features::disable_feature(pool, chat_id, feat, user_id).await;
            }
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Category '{}' disabled ({} features).", escape_md_v2(category), feats.len()),
                )
                .await;
        }
        None => {
            let _ = bot
                .send_message(msg.chat.id, "Category not found.")
                .await;
        }
    }
    Ok(())
}

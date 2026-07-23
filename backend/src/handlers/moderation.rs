use sqlx::PgPool;
use teloxide::prelude::*;

use crate::auth::extract_target_user;
use crate::config::Settings;
use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

async fn send_text(bot: &Bot, chat_id: ChatId, text: &str) {
    let _ = bot.send_message(chat_id, text).await;
}

async fn extract_target(bot: &Bot, msg: &Message, usage: &str) -> Option<(i64, String)> {
    match extract_target_user(msg) {
        Some((id, name)) if id != 0 => Some((id, name)),
        Some((0, name)) => {
            if let Some(resolved) = crate::auth::resolve_username(bot, msg.chat.id, &name).await {
                Some(resolved)
            } else {
                send_text(
                    bot,
                    msg.chat.id,
                    &format!(
                        "Could not resolve user {}. Reply to their message instead.",
                        name
                    ),
                )
                .await;
                None
            }
        }
        _ => {
            send_text(bot, msg.chat.id, usage).await;
            None
        }
    }
}

pub async fn handle_ban(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /ban @username").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    match bot
        .ban_chat_member(msg.chat.id, UserId(target_id as u64))
        .await
    {
        Ok(_) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Banned {}", escape_md_v2(&target_name)),
            )
            .await;
            log_mod_action(
                &bot,
                settings,
                msg.chat.id,
                &format!(
                    "Banned {} in {} (by {})",
                    escape_md_v2(&target_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group")),
                    escape_md_v2(executor)
                ),
            )
            .await;
        }
        Err(e) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to ban: {}", escape_md_v2(&e.to_string())),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_unban(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /unban @username").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    match bot
        .unban_chat_member(msg.chat.id, UserId(target_id as u64))
        .await
    {
        Ok(_) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Unbanned {}", escape_md_v2(&target_name)),
            )
            .await;
            log_mod_action(
                &bot,
                settings,
                msg.chat.id,
                &format!(
                    "Unbanned {} in {} (by {})",
                    escape_md_v2(&target_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group")),
                    escape_md_v2(executor)
                ),
            )
            .await;
        }
        Err(e) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to unban: {}", escape_md_v2(&e.to_string())),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_kick(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /kick @username").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    if let Err(e) = bot
        .ban_chat_member(msg.chat.id, UserId(target_id as u64))
        .await
    {
        send_text(
            &bot,
            msg.chat.id,
            &format!("Failed to kick: {}", escape_md_v2(&e.to_string())),
        )
        .await;
        return Ok(());
    }
    let _ = tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    let _ = bot
        .unban_chat_member(msg.chat.id, UserId(target_id as u64))
        .await;
    send_text(
        &bot,
        msg.chat.id,
        &format!("Kicked {}", escape_md_v2(&target_name)),
    )
    .await;
    log_mod_action(
        &bot,
        settings,
        msg.chat.id,
        &format!(
            "Kicked {} in {} (by {})",
            escape_md_v2(&target_name),
            escape_md_v2(msg.chat.title().unwrap_or("group")),
            escape_md_v2(executor)
        ),
    )
    .await;
    Ok(())
}

pub async fn handle_mute(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /mute @username").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    let permissions = teloxide::types::ChatPermissions::empty();
    match bot
        .restrict_chat_member(msg.chat.id, UserId(target_id as u64), permissions)
        .await
    {
        Ok(_) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Muted {}", escape_md_v2(&target_name)),
            )
            .await;
            log_mod_action(
                &bot,
                settings,
                msg.chat.id,
                &format!(
                    "Muted {} in {} (by {})",
                    escape_md_v2(&target_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group")),
                    escape_md_v2(executor)
                ),
            )
            .await;
        }
        Err(e) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to mute: {}", escape_md_v2(&e.to_string())),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_unmute(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /unmute @username").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    let permissions = teloxide::types::ChatPermissions::all();
    match bot
        .restrict_chat_member(msg.chat.id, UserId(target_id as u64), permissions)
        .await
    {
        Ok(_) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Unmuted {}", escape_md_v2(&target_name)),
            )
            .await;
            log_mod_action(
                &bot,
                settings,
                msg.chat.id,
                &format!(
                    "Unmuted {} in {} (by {})",
                    escape_md_v2(&target_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group")),
                    escape_md_v2(executor)
                ),
            )
            .await;
        }
        Err(e) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to unmute: {}", escape_md_v2(&e.to_string())),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_warn(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /warn @user [reason]").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let chat_id = msg.chat.id.0;
    let warned_by = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);

    let reason = msg
        .text()
        .map(|t| {
            let parts: Vec<&str> = t.splitn(3, ' ').collect();
            if parts.len() >= 3 {
                parts[2]
            } else {
                "No reason provided"
            }
        })
        .unwrap_or("No reason provided");

    let _ = crate::db::warnings::add_warning(pool, chat_id, target_id, reason, warned_by).await;
    let count = crate::db::warnings::get_warning_count(pool, chat_id, target_id)
        .await
        .unwrap_or(0);

    send_text(
        &bot,
        msg.chat.id,
        &format!(
            "{} has been warned. ({}/{})\nReason: {}",
            escape_md_v2(&target_name),
            count,
            settings.warn_threshold,
            escape_md_v2(reason)
        ),
    )
    .await;

    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    log_mod_action(
        &bot,
        settings,
        msg.chat.id,
        &format!(
            "Warned {} ({}/{}) in {} by {} — {}",
            escape_md_v2(&target_name),
            count,
            settings.warn_threshold,
            escape_md_v2(msg.chat.title().unwrap_or("group")),
            escape_md_v2(executor),
            escape_md_v2(reason)
        ),
    )
    .await;

    if count >= settings.warn_threshold as i64 {
        let _ = bot
            .ban_chat_member(msg.chat.id, UserId(target_id as u64))
            .await;
        send_text(
            &bot,
            msg.chat.id,
            &format!(
                "{} auto-banned for exceeding warn threshold.",
                escape_md_v2(&target_name)
            ),
        )
        .await;
        log_mod_action(
            &bot,
            settings,
            msg.chat.id,
            &format!(
                "Auto-banned {} in {} (exceeded warn threshold)",
                escape_md_v2(&target_name),
                escape_md_v2(msg.chat.title().unwrap_or("group"))
            ),
        )
        .await;
        let _ = crate::db::warnings::reset_warnings(pool, chat_id, target_id).await;
    }
    Ok(())
}

pub async fn handle_warns(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /warns @user").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let chat_id = msg.chat.id.0;
    let count = crate::db::warnings::get_warning_count(pool, chat_id, target_id)
        .await
        .unwrap_or(0);
    let warnings = crate::db::warnings::get_warnings(pool, chat_id, target_id)
        .await
        .unwrap_or_default();

    let mut text = format!("Warnings for {}: {}/3\n", escape_md_v2(&target_name), count);
    for (i, (_id, reason, by)) in warnings.iter().enumerate() {
        text.push_str(&format!(
            "{}. {} (by {})\n",
            i + 1,
            escape_md_v2(reason),
            by
        ));
    }
    if warnings.is_empty() {
        text.push_str("No warnings.");
    }

    send_text(&bot, msg.chat.id, &text).await;
    Ok(())
}

pub async fn handle_resetwarn(
    bot: Bot,
    msg: Message,
    pool: &PgPool,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, "Usage: Reply to a user or /resetwarn @user").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let chat_id = msg.chat.id.0;
    let removed = crate::db::warnings::reset_warnings(pool, chat_id, target_id)
        .await
        .unwrap_or(0);
    send_text(
        &bot,
        msg.chat.id,
        &format!(
            "Reset {} warning(s) for {}.",
            removed,
            escape_md_v2(&target_name)
        ),
    )
    .await;
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    log_mod_action(
        &bot,
        settings,
        msg.chat.id,
        &format!(
            "Reset {} warning(s) for {} in {} (by {})",
            removed,
            escape_md_v2(&target_name),
            escape_md_v2(msg.chat.title().unwrap_or("group")),
            escape_md_v2(executor)
        ),
    )
    .await;
    Ok(())
}

pub async fn handle_slowmode(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    if parts.len() < 2 {
        send_text(
            &bot,
            msg.chat.id,
            "Usage: /slowmode <seconds>\nUse 0 to disable.",
        )
        .await;
        return Ok(());
    }
    let seconds: u32 = match parts[1].parse() {
        Ok(v) => v,
        Err(_) => {
            send_text(&bot, msg.chat.id, "Invalid number.").await;
            return Ok(());
        }
    };
    let api_url = format!(
        "https://api.telegram.org/bot{}/setChatSlowMode",
        settings.bot_token
    );
    match bot
        .client()
        .post(&api_url)
        .json(&serde_json::json!({
            "chat_id": msg.chat.id,
            "slow_mode_delay": seconds
        }))
        .send()
        .await
    {
        Ok(r) if r.status().is_success() => {
            if seconds == 0 {
                send_text(&bot, msg.chat.id, "Slowmode disabled.").await;
            } else {
                send_text(
                    &bot,
                    msg.chat.id,
                    &format!("Slowmode set to {} seconds.", seconds),
                )
                .await;
            }
        }
        Ok(_) => {
            send_text(
                &bot,
                msg.chat.id,
                "Failed to set slowmode. Check bot permissions.",
            )
            .await;
        }
        Err(e) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Network error: {}", escape_md_v2(&e.to_string())),
            )
            .await;
        }
    }
    Ok(())
}

pub async fn handle_del(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    if let Some(reply) = msg.reply_to_message() {
        match bot.delete_message(msg.chat.id, reply.id).await {
            Ok(_) => {
                let _ = bot.delete_message(msg.chat.id, msg.id).await;
                let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
                log_mod_action(
                    &bot,
                    settings,
                    msg.chat.id,
                    &format!(
                        "Deleted message in {} (by {})",
                        escape_md_v2(msg.chat.title().unwrap_or("group")),
                        escape_md_v2(executor)
                    ),
                )
                .await;
            }
            Err(e) => {
                send_text(
                    &bot,
                    msg.chat.id,
                    &format!("Failed to delete: {}", escape_md_v2(&e.to_string())),
                )
                .await
            }
        }
    } else {
        send_text(
            &bot,
            msg.chat.id,
            "Reply to the message you want to delete.",
        )
        .await;
    }
    Ok(())
}

pub async fn handle_pin(
    bot: Bot,
    msg: Message,
    settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    if let Some(reply) = msg.reply_to_message() {
        match bot.pin_chat_message(msg.chat.id, reply.id).await {
            Ok(_) => {
                let _ = bot.delete_message(msg.chat.id, msg.id).await;
                let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
                log_mod_action(
                    &bot,
                    settings,
                    msg.chat.id,
                    &format!(
                        "Pinned message in {} (by {})",
                        escape_md_v2(msg.chat.title().unwrap_or("group")),
                        escape_md_v2(executor)
                    ),
                )
                .await;
            }
            Err(e) => {
                send_text(
                    &bot,
                    msg.chat.id,
                    &format!("Failed to pin: {}", escape_md_v2(&e.to_string())),
                )
                .await
            }
        }
    } else {
        send_text(&bot, msg.chat.id, "Reply to the message you want to pin.").await;
    }
    Ok(())
}

use crate::telegram::api::Bot;
use crate::telegram::update::{ChatPermissions, Message};
use tokio_postgres::Client;

use crate::auth::extract_target_user;
use crate::config::Settings;
use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

async fn send_text(bot: &Bot, chat_id: i64, text: &str) {
    let _ = bot.send_message(chat_id, text).await;
}

async fn extract_target(bot: &Bot, msg: &Message, client: &Client, usage: &str) -> Option<(i64, String)> {
    match extract_target_user(msg) {
        Some((id, name)) if id != 0 => Some((id, name)),
        Some((0, name)) => {
            if let Some(resolved) = crate::auth::resolve_username(bot, msg.chat.id, &name).await {
                Some(resolved)
            } else {
                // Try resolving from database cache
                let clean_uname = name.trim_start_matches('@').to_lowercase();
                match client.query_one("SELECT user_id, first_name FROM username_cache WHERE username = $1", &[&clean_uname]).await {
                    Ok(row) => {
                        let user_id: i64 = row.get(0);
                        let first_name: String = row.get(1);
                        Some((user_id, first_name))
                    }
                    Err(_) => {
                        let command_name = msg.text()
                            .and_then(|t| t.split_whitespace().next())
                            .and_then(|cmd| cmd.strip_prefix('/'))
                            .map(|cmd| cmd.split('@').next().unwrap_or(cmd))
                            .unwrap_or("unban");
                        send_text(
                            bot,
                            msg.chat.id,
                            &format!(
                                "[Pending] User {} not found in cache. Reply to this message with their Numeric ID to complete the {} command.",
                                name,
                                command_name
                            ),
                        )
                        .await;
                        None
                    }
                }
            }
        }
        _ => {
            send_text(bot, msg.chat.id, usage).await;
            None
        }
    }
}

pub async fn handle_ban(bot: Bot, msg: Message, client: &Client, settings: &Settings) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /ban @username").await {
            Some(v) => v,
            None => {
                tracing::warn!("Failed to extract target user for ban command");
                return Ok(());
            }
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    tracing::info!(target_id = %target_id, target_name = %target_name, executor = %executor, "Executing /ban command");
    match bot.ban_chat_member(msg.chat.id, target_id as u64).await {
        Ok(_) => {
            tracing::info!(target_id = %target_id, "Telegram banChatMember API call succeeded");
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
            tracing::error!(target_id = %target_id, error = %e, "Telegram banChatMember API call failed");
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to ban: {}", escape_md_v2(&e)),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_unban(bot: Bot, msg: Message, client: &Client, settings: &Settings) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /unban @username").await {
            Some(v) => v,
            None => {
                tracing::warn!("Failed to extract target user for unban command");
                return Ok(());
            }
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    tracing::info!(target_id = %target_id, target_name = %target_name, executor = %executor, "Executing /unban command");
    match bot.unban_chat_member(msg.chat.id, target_id as u64).await {
        Ok(_) => {
            tracing::info!(target_id = %target_id, "Telegram unbanChatMember API call succeeded");

            // Get the invite link
            let group_title = msg.chat.title().unwrap_or("the group");
            let mut invite_link_str = String::new();
            let mut invite_sent_message = String::new();

            match bot.export_chat_invite_link(msg.chat.id).await {
                Ok(link) => {
                    invite_link_str = link;
                }
                Err(err) => {
                    tracing::warn!(chat_id = %msg.chat.id, error = %err, "Failed to export chat invite link, trying username");
                    if let Some(ref username) = msg.chat.username {
                        invite_link_str = format!("https://t.me/{}", username);
                    }
                }
            }

            if !invite_link_str.is_empty() {
                let dm_text = format!(
                    "You have been unbanned in {}.\n\nHere is the link to join back:\n{}",
                    group_title,
                    invite_link_str
                );
                match bot.send_message(target_id, dm_text).await {
                    Ok(_) => {
                        tracing::info!(target_id = %target_id, "Direct message with group invite link sent successfully");
                        invite_sent_message = " 📬 Invite link sent to their DMs.".to_string();
                    }
                    Err(dm_err) => {
                        tracing::warn!(target_id = %target_id, error = %dm_err, "Failed to DM invite link to unbanned user");
                        invite_sent_message = format!(" ⚠️ Could not send DM (Error: {}).", dm_err);
                    }
                }
            } else {
                invite_sent_message = " ⚠️ Could not generate invite link for group.".to_string();
            }

            send_text(
                &bot,
                msg.chat.id,
                &format!("Unbanned {}.{}", escape_md_v2(&target_name), invite_sent_message),
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
            tracing::error!(target_id = %target_id, error = %e, "Telegram unbanChatMember API call failed");
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to unban: {}", escape_md_v2(&e)),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_kick(bot: Bot, msg: Message, client: &Client, settings: &Settings) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /kick @username").await {
            Some(v) => v,
            None => {
                tracing::warn!("Failed to extract target user for kick command");
                return Ok(());
            }
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    tracing::info!(target_id = %target_id, target_name = %target_name, executor = %executor, "Executing /kick command (ban-then-unban)");
    match bot.ban_chat_member(msg.chat.id, target_id as u64).await {
        Ok(_) => {
            tracing::info!(target_id = %target_id, "Telegram banChatMember (part of kick) succeeded");
            // Unban immediately to complete the kick (allows re-joining)
            let unban_res = bot.unban_chat_member(msg.chat.id, target_id as u64).await;
            tracing::info!(target_id = %target_id, result = ?unban_res, "Telegram unbanChatMember (part of kick) completed");
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
        }
        Err(e) => {
            tracing::error!(target_id = %target_id, error = %e, "Telegram banChatMember (part of kick) failed");
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to kick: {}", escape_md_v2(&e)),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_mute(bot: Bot, msg: Message, client: &Client, settings: &Settings) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /mute @username").await {
            Some(v) => v,
            None => {
                tracing::warn!("Failed to extract target user for mute command");
                return Ok(());
            }
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    let permissions = ChatPermissions::empty();
    tracing::info!(target_id = %target_id, target_name = %target_name, executor = %executor, "Executing /mute command");
    match bot
        .restrict_chat_member(msg.chat.id, target_id as u64, permissions)
        .await
    {
        Ok(_) => {
            tracing::info!(target_id = %target_id, "Telegram restrictChatMember (mute) succeeded");
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
            tracing::error!(target_id = %target_id, error = %e, "Telegram restrictChatMember (mute) failed");
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to mute: {}", escape_md_v2(&e)),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_unmute(bot: Bot, msg: Message, client: &Client, settings: &Settings) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /unmute @username").await {
            Some(v) => v,
            None => {
                tracing::warn!("Failed to extract target user for unmute command");
                return Ok(());
            }
        };
    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    let permissions = ChatPermissions::all();
    tracing::info!(target_id = %target_id, target_name = %target_name, executor = %executor, "Executing /unmute command");
    match bot
        .restrict_chat_member(msg.chat.id, target_id as u64, permissions)
        .await
    {
        Ok(_) => {
            tracing::info!(target_id = %target_id, "Telegram restrictChatMember (unmute) succeeded");
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
            tracing::error!(target_id = %target_id, error = %e, "Telegram restrictChatMember (unmute) failed");
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to unmute: {}", escape_md_v2(&e)),
            )
            .await
        }
    }
    Ok(())
}

pub async fn handle_warn(
    bot: Bot,
    msg: Message,
    client: &Client,
    settings: &Settings,
) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /warn @user [reason]").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let chat_id = msg.chat.id;
    let warned_by = msg.from().map(|u| u.id as i64).unwrap_or(0);

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

    let _ = crate::db::warnings::add_warning(client, chat_id, target_id, reason, warned_by).await;
    let count = crate::db::warnings::get_warning_count(client, chat_id, target_id)
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
        let _ = bot.ban_chat_member(msg.chat.id, target_id as u64).await;
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
        let _ = crate::db::warnings::reset_warnings(client, chat_id, target_id).await;
    }
    Ok(())
}

pub async fn handle_warns(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /warns @user").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let chat_id = msg.chat.id;
    let count = crate::db::warnings::get_warning_count(client, chat_id, target_id)
        .await
        .unwrap_or(0);
    let warnings = crate::db::warnings::get_warnings(client, chat_id, target_id)
        .await
        .unwrap_or_default();

    // Try to get the warn threshold from environment settings (default 3)
    let threshold: i64 = std::env::var("WARN_THRESHOLD")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(3);

    let mut text = format!("Warnings for {}: {} /{}\n", escape_md_v2(&target_name), count, threshold);
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
    client: &Client,
    settings: &Settings,
) -> Result<(), String> {
    let (target_id, target_name) =
        match extract_target(&bot, &msg, client, "Usage: Reply to a user or /resetwarn @user").await {
            Some(v) => v,
            None => return Ok(()),
        };
    let chat_id = msg.chat.id;
    let removed = crate::db::warnings::reset_warnings(client, chat_id, target_id)
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

pub async fn handle_slowmode(bot: Bot, msg: Message, _settings: &Settings) -> Result<(), String> {
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
    match bot
        .api_post(
            "setChatSlowMode",
            serde_json::json!({
                "chat_id": msg.chat.id,
                "slow_mode_delay": seconds
            }),
        )
        .await
    {
        Ok(_) => {
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
        Err(e) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Failed to set slowmode: {}", escape_md_v2(&e)),
            )
            .await;
        }
    }
    Ok(())
}

pub async fn handle_del(bot: Bot, msg: Message, settings: &Settings) -> Result<(), String> {
    if let Some(reply) = msg.reply_to_message() {
        match bot.delete_message(msg.chat.id, reply.id()).await {
            Ok(_) => {
                let _ = bot.delete_message(msg.chat.id, msg.id()).await;
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
                    &format!("Failed to delete: {}", escape_md_v2(&e)),
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

pub async fn handle_pin(bot: Bot, msg: Message, settings: &Settings) -> Result<(), String> {
    if let Some(reply) = msg.reply_to_message() {
        match bot.pin_chat_message(msg.chat.id, reply.id()).await {
            Ok(_) => {
                let _ = bot.delete_message(msg.chat.id, msg.id()).await;
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
                    &format!("Failed to pin: {}", escape_md_v2(&e)),
                )
                .await
            }
        }
    } else {
        send_text(&bot, msg.chat.id, "Reply to the message you want to pin.").await;
    }
    Ok(())
}

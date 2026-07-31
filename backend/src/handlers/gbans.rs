use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

async fn send_text(bot: &Bot, chat_id: i64, text: &str) {
    let _ = bot.send_message(chat_id, text).await;
}

/// /gban @user <reason> — ban a user in every group the bot manages.
pub async fn handle_gban(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let sender_id = msg.from().map(|u| u.id).unwrap_or(0);
    if !crate::auth::is_sudo_or_privileged(sender_id) {
        send_text(
            &bot,
            msg.chat.id,
            "This command is restricted to bot operators.",
        )
        .await;
        return Ok(());
    }

    let text = msg.text().unwrap_or("");
    let rest = text.strip_prefix("/gban").unwrap_or("").trim();
    let parts: Vec<&str> = rest.splitn(2, ' ').collect();
    let target_text = parts.first().copied().unwrap_or("");
    let reason = parts
        .get(1)
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .unwrap_or("No reason provided");

    if target_text.is_empty() {
        send_text(&bot, msg.chat.id, "Usage: /gban @user <reason>").await;
        return Ok(());
    }

    let mut mock = msg.clone();
    mock.text = Some(format!("/gban {}", target_text));
    let (target_id, target_name) = match crate::auth::extract_target_user(&mock) {
        Some((0, name)) => match crate::auth::resolve_username(&bot, msg.chat.id, &name).await {
            Some(v) => v,
            None => {
                let clean_uname = name.trim_start_matches('@').to_lowercase();
                match client
                    .query_one(
                        "SELECT user_id, first_name FROM username_cache WHERE username = $1",
                        &[&clean_uname],
                    )
                    .await
                {
                    Ok(row) => (
                        row.get::<_, i64>(0),
                        crate::crypto::try_decrypt(&row.get::<_, String>(1)),
                    ),
                    Err(_) => {
                        send_text(
                            &bot,
                            msg.chat.id,
                            "User not found. Reply to their message or use their numeric ID.",
                        )
                        .await;
                        return Ok(());
                    }
                }
            }
        },
        Some((id, name)) if id != 0 => (id, name),
        _ => {
            send_text(&bot, msg.chat.id, "Usage: /gban @user <reason>").await;
            return Ok(());
        }
    };

    // Record the gban first.
    if let Err(e) = crate::db::gbans::add_gban(
        client,
        target_id,
        &target_name,
        reason,
        msg.from().map(|u| u.id as i64).unwrap_or(0),
    )
    .await
    {
        send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await;
        return Ok(());
    }

    // Ban the user from every group the bot knows about.
    let groups = crate::db::groups::list_groups(client)
        .await
        .unwrap_or_default();
    let mut banned_in = 0usize;
    for gid in groups {
        if bot.ban_chat_member(gid, target_id as u64).await.is_ok() {
            banned_in += 1;
        }
    }

    send_text(
        &bot,
        msg.chat.id,
        &format!(
            "Globally banned {} in {} group(s).\nReason: {}",
            escape_md_v2(&target_name),
            banned_in,
            escape_md_v2(reason)
        ),
    )
    .await;

    let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
    log_mod_action(
        &bot,
        crate::config::Settings::global(),
        msg.chat.id,
        &format!(
            "GBan {} in {} groups — {} (by {})",
            escape_md_v2(&target_name),
            banned_in,
            escape_md_v2(reason),
            escape_md_v2(executor)
        ),
    )
    .await;
    Ok(())
}

/// /ungban @user — remove a user from the global ban list.
pub async fn handle_ungban(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let sender_id = msg.from().map(|u| u.id).unwrap_or(0);
    if !crate::auth::is_sudo_or_privileged(sender_id) {
        send_text(
            &bot,
            msg.chat.id,
            "This command is restricted to bot operators.",
        )
        .await;
        return Ok(());
    }

    let text = msg.text().unwrap_or("");
    let target_text = text
        .strip_prefix("/ungban")
        .unwrap_or("")
        .split_whitespace()
        .next()
        .unwrap_or("")
        .to_string();

    if target_text.is_empty() {
        send_text(&bot, msg.chat.id, "Usage: /ungban @user").await;
        return Ok(());
    }

    let mut mock = msg.clone();
    mock.text = Some(format!("/ungban {}", target_text));
    let (target_id, target_name) = match crate::auth::extract_target_user(&mock) {
        Some((id, name)) if id != 0 => (id, name),
        Some((0, name)) => match crate::auth::resolve_username(&bot, msg.chat.id, &name).await {
            Some(v) => v,
            None => {
                let clean_uname = name.trim_start_matches('@').to_lowercase();
                match client
                    .query_one(
                        "SELECT user_id, first_name FROM username_cache WHERE username = $1",
                        &[&clean_uname],
                    )
                    .await
                {
                    Ok(row) => (
                        row.get::<_, i64>(0),
                        crate::crypto::try_decrypt(&row.get::<_, String>(1)),
                    ),
                    Err(_) => {
                        send_text(&bot, msg.chat.id, "User not found.").await;
                        return Ok(());
                    }
                }
            }
        },
        _ => {
            send_text(&bot, msg.chat.id, "Usage: /ungban @user").await;
            return Ok(());
        }
    };

    match crate::db::gbans::remove_gban(client, target_id).await {
        Ok(true) => {
            send_text(
                &bot,
                msg.chat.id,
                &format!(
                    "Removed {} from the global ban list.",
                    escape_md_v2(&target_name)
                ),
            )
            .await;
            let executor = msg.from().map(|u| u.first_name.as_str()).unwrap_or("Admin");
            log_mod_action(
                &bot,
                crate::config::Settings::global(),
                msg.chat.id,
                &format!(
                    "Un-gbanned {} in {} (by {})",
                    escape_md_v2(&target_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group")),
                    escape_md_v2(executor)
                ),
            )
            .await;
        }
        Ok(false) => send_text(&bot, msg.chat.id, "That user is not globally banned.").await,
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

/// /gbans — list all globally banned users.
pub async fn handle_gbans_list(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let sender_id = msg.from().map(|u| u.id).unwrap_or(0);
    if !crate::auth::is_sudo_or_privileged(sender_id) {
        send_text(
            &bot,
            msg.chat.id,
            "This command is restricted to bot operators.",
        )
        .await;
        return Ok(());
    }

    match crate::db::gbans::list_gbans(client).await {
        Ok(gbans) => {
            if gbans.is_empty() {
                send_text(&bot, msg.chat.id, "The global ban list is empty.").await;
            } else {
                let mut text = format!("*🌐 Global Bans ({}):*\n", gbans.len());
                for g in &gbans {
                    text.push_str(&format!(
                        "• {} (`{}`) — {}\n",
                        escape_md_v2(&g.user_name),
                        g.user_id,
                        escape_md_v2(&g.reason)
                    ));
                }
                let _ = bot
                    .send_message(msg.chat.id, text)
                    .parse_mode(crate::telegram::ParseMode::MarkdownV2)
                    .await;
            }
        }
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

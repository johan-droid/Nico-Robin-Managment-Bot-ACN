use crate::telegram::api::Bot;
use crate::telegram::ParseMode;
use crate::telegram::update::Message;
use tokio_postgres::Client;

use crate::auth::extract_target_user;
use crate::utils::escape_md_v2;

/// Resolve the user a `/profile` command is targeting.
/// Prefers reply / `text_mention`, then `@username` (admins + DB cache),
/// then falls back to the sender.
async fn resolve_profile_target(
    bot: &Bot,
    msg: &Message,
    client: &Client,
) -> Result<(i64, String), String> {
    match extract_target_user(msg) {
        Some((id, name)) if id != 0 => Ok((id, name)),
        Some((0, name)) => {
            if let Some(resolved) = crate::auth::resolve_username(bot, msg.chat.id, &name).await {
                return Ok(resolved);
            }
            let clean_uname = name.trim_start_matches('@').to_lowercase();
            match client
                .query_one(
                    "SELECT user_id, first_name FROM username_cache WHERE username = $1",
                    &[&clean_uname],
                )
                .await
            {
                Ok(row) => {
                    let uid = row.get::<_, i64>(0);
                    let cached_name = crate::crypto::try_decrypt(&row.get::<_, String>(1));
                    Ok((uid, cached_name))
                }
                Err(_) => Err(format!("Could not resolve user {}.", escape_md_v2(&name))),
            }
        }
        _ => Ok((
            msg.from().map(|u| u.id as i64).unwrap_or(0),
            msg.from().map(|u| u.first_name.clone()).unwrap_or_default(),
        )),
    }
}

/// Maps a Telegram `ChatMember.status` to a friendly, emoji-rich label.
fn format_status(status: &str) -> &'static str {
    match status {
        "creator" => "👑 Owner",
        "administrator" => "🛡️ Admin",
        "member" => "👤 Member",
        "restricted" => "⏳ Restricted",
        "left" => "🚪 Left",
        "kicked" => "🚫 Banned",
        _ => "❔ Unknown",
    }
}

/// Builds the custom profile card shown under the profile picture.
fn build_profile_card(
    name: &str,
    username: Option<&str>,
    user_id: i64,
    status: Option<&str>,
    is_group: bool,
    bio: &str,
    group_title: Option<&str>,
) -> String {
    let mut card = String::from(
        "🌺 *NICO ROBIN — PROFILE* 🌺\n\
         ✿ ∘ ━━━━━━━━━━━━━━┉┅╍\n\n",
    );

    card.push_str(&format!("👤 *Name:* {}\n", escape_md_v2(name)));
    match username {
        Some(u) => card.push_str(&format!("📛 *Username:* @{}\n", escape_md_v2(u))),
        None => card.push_str("📛 *Username:* None\n"),
    }
    card.push_str(&format!("🆔 *User ID:* `{}`\n", user_id));

    if is_group {
        match status {
            Some(s) => {
                card.push_str(&format!("🎖 *Role:* {}\n", format_status(s)));
            }
            None => {
                card.push_str("🎖 *Role:* —\n");
            }
        }
    } else {
        card.push_str("💬 *Chat:* Private\n");
    }

    let bio_text = if bio.trim().is_empty() {
        "_No bio set yet — use /setbio to add one._".to_string()
    } else {
        escape_md_v2(bio.trim())
    };
    card.push_str(&format!("\n📝 *Bio:*\n{}\n", bio_text));

    card.push_str("\n✿ ∘ ━━━━━━━━━━━━━━┉┅╍\n");
    if let Some(title) = group_title {
        card.push_str(&format!("🗂 *Group:* {}\n", escape_md_v2(title)));
    }
    card.push_str("🌺 *Nico Robin Bot* 🌺");
    card
}

pub async fn handle_profile(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let (target_id, fallback_name) = match resolve_profile_target(&bot, &msg, client).await {
        Ok(v) => v,
        Err(e) => {
            let _ = bot.send_message(msg.chat.id, e).await;
            return Ok(());
        }
    };
    if target_id == 0 {
        bot.send_message(msg.chat.id, "Could not resolve user.")
            .await?;
        return Ok(());
    }

    let is_group = msg.chat.is_group() || msg.chat.is_supergroup();
    let member = if is_group {
        bot.get_chat_member(msg.chat.id, target_id as u64).await.ok()
    } else {
        None
    };

    let name = member
        .as_ref()
        .map(|m| m.user.first_name.clone())
        .unwrap_or(fallback_name);
    let username = member.as_ref().and_then(|m| m.user.username.clone());
    let status = member.as_ref().map(|m| m.status.clone());

    // Bio from the user-profiles table.
    let bio = crate::db::profiles::get_or_create_profile(client, target_id)
        .await
        .map(|p| p.bio)
        .unwrap_or_default();

    let group_title = if is_group { msg.chat.title() } else { None };

    let card = build_profile_card(
        &name,
        username.as_deref(),
        target_id,
        status.as_deref(),
        is_group,
        &bio,
        group_title,
    );

    // Prefer sending the profile picture with the card as its caption.
    if let Ok(Some(photo)) = bot.get_user_profile_photo(target_id as u64).await {
        if let Ok(file_path) = bot.get_file_path(&photo.file_id).await {
            if let Ok(bytes) = bot.download_file(&file_path).await {
                let filename = if file_path.to_lowercase().ends_with(".png") {
                    "profile.png"
                } else {
                    "profile.jpg"
                };
                let sent = bot
                    .send_photo_file(
                        msg.chat.id,
                        filename,
                        bytes,
                        Some(card.clone()),
                        Some(ParseMode::MarkdownV2),
                        None,
                    )
                    .await;
                if sent.is_ok() {
                    return Ok(());
                }
            }
        }
    }

    // Fallback: text-only profile card.
    let _ = bot
        .send_message(msg.chat.id, card)
        .parse_mode(ParseMode::MarkdownV2)
        .await;
    Ok(())
}

pub async fn handle_setbio(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let content = text.strip_prefix("/setbio ").unwrap_or("");
    if content.is_empty() {
        bot.send_message(msg.chat.id, "Usage: /setbio <your bio>")
            .await?;
        return Ok(());
    }
    let user_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    match crate::db::profiles::set_bio(client, user_id, content).await {
        Ok(_) => {
            let _ = bot.send_message(msg.chat.id, "Bio updated.").await;
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

pub async fn handle_export(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    match crate::db::profiles::get_or_create_profile(client, user_id).await {
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
                .parse_mode(ParseMode::MarkdownV2)
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

pub async fn handle_delete_data(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let caller_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    let target_id = match extract_target_user(&msg) {
        Some((id, _)) if id > 0 => id,
        _ => caller_id,
    };

    match crate::db::profiles::delete_profile(client, target_id).await {
        Ok(true) => {
            if target_id == caller_id {
                let _ = bot.send_message(msg.chat.id, "Your data has been deleted.").await;
            } else {
                let _ = bot
                    .send_message(msg.chat.id, "The user's data has been deleted.")
                    .await;
            }
        }
        Ok(false) => {
            let _ = bot.send_message(msg.chat.id, "No data found to delete.").await;
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

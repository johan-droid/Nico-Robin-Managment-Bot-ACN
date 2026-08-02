use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use crate::telegram::ParseMode;
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
            let username_hash = crate::crypto::try_crypto()
                .map(|c| c.hash_text(&clean_uname))
                .unwrap_or_default();
            
            let row_res = if username_hash.is_empty() {
                client
                    .query_one(
                        "SELECT user_id, first_name FROM username_cache WHERE username = $1",
                        &[&clean_uname],
                    )
                    .await
            } else {
                client
                    .query_one(
                        "SELECT user_id, first_name FROM username_cache WHERE username_hash = $1",
                        &[&username_hash],
                    )
                    .await
            };

            match row_res {
                Ok(row) => {
                    let uid: i64 = row.get(0);
                    let fname: String = crate::crypto::try_decrypt(&row.get::<_, String>(1));
                    Ok((uid, fname))
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
        "_No bio set yet_ — use /setbio to add one".to_string()
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
        bot.get_chat_member(msg.chat.id, target_id as u64)
            .await
            .ok()
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
    // Telegram lets us send the freshly-fetched `file_id` directly — no
    // download / re-upload needed, which keeps the command fast and reliable.
    if let Ok(Some(photo)) = bot.get_user_profile_photo(target_id as u64).await {
        let sent = bot
            .send_photo(msg.chat.id, photo.file_id.clone())
            .caption(Some(card.clone()))
            .parse_mode(ParseMode::MarkdownV2)
            .await;
        if sent.is_ok() {
            return Ok(());
        }
        tracing::warn!(
            target_id = %target_id,
            error = %sent.unwrap_err(),
            "Profile photo send failed, falling back to text"
        );
    }

    // Fallback: text-only profile card. Try MarkdownV2 first, then plain
    // text so the user always gets a response even if parsing fails.
    match bot
        .send_message(msg.chat.id, card.clone())
        .parse_mode(ParseMode::MarkdownV2)
        .await
    {
        Ok(_) => Ok(()),
        Err(e) => {
            tracing::warn!(
                target_id = %target_id,
                error = %e,
                "MarkdownV2 profile card failed, sending plain text"
            );
            let _ = bot.send_message(msg.chat.id, strip_md_v2(&card)).await;
            Ok(())
        }
    }
}

/// Removes MarkdownV2 formatting markers so the card can be shown as plain text.
fn strip_md_v2(text: &str) -> String {
    text.replace(['*', '`', '_'], "")
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
                let _ = bot
                    .send_message(msg.chat.id, "Your data has been deleted.")
                    .await;
            } else {
                let _ = bot
                    .send_message(msg.chat.id, "The user's data has been deleted.")
                    .await;
            }
        }
        Ok(false) => {
            let _ = bot
                .send_message(msg.chat.id, "No data found to delete.")
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn profile_card_renders_valid_markdown() {
        let card = build_profile_card(
            "John Doe",
            Some("johndoe"),
            123456789,
            Some("creator"),
            true,
            "",
            Some("ACN Test Group"),
        );

        // The card must contain the key fields.
        assert!(card.contains("*Name:* John Doe"), "missing name:\n{card}");
        assert!(
            card.contains("*Username:* @johndoe"),
            "missing username:\n{card}"
        );
        assert!(
            card.contains("*User ID:* `123456789`"),
            "missing id:\n{card}"
        );
        assert!(card.contains("*Role:* 👑 Owner"), "missing role:\n{card}");
        assert!(
            card.contains("*Group:* ACN Test Group"),
            "missing group:\n{card}"
        );

        // The empty-bio placeholder must be valid MarkdownV2: the italic span
        // must NOT contain an unescaped `.` or `!` (they break parsing).
        assert!(
            !card.contains("add one._"),
            "unescaped '.' inside italic span:\n{card}"
        );
        assert!(
            card.contains("_No bio set yet_ — use /setbio to add one"),
            "missing safe placeholder:\n{card}"
        );
    }

    #[test]
    fn profile_card_escapes_user_content() {
        let card = build_profile_card(
            "A.B!C",
            Some("user_name"),
            42,
            None,
            false,
            "Bio with . and ! chars.",
            None,
        );
        // User-controlled dots must be escaped for MarkdownV2.
        assert!(card.contains("A\\.B\\!C"), "name not escaped:\n{card}");
        assert!(
            card.contains("Bio with \\. and \\! chars\\."),
            "bio not escaped:\n{card}"
        );
    }

    #[test]
    fn strip_md_v2_removes_markers() {
        assert_eq!(strip_md_v2("*Name:* `123` _text_"), "Name: 123 text");
    }
}

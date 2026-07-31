use crate::telegram::api::Bot;
use crate::telegram::update::{Message, MessageEntity};
use tokio_postgres::Client;

use crate::utils::escape_md_v2;

const LOCK_TYPES: &[&str] = &[
    "photos", "videos", "stickers", "gifs", "documents", "voice", "audio", "links",
    "forward", "bots", "polls", "video_notes",
];

async fn send_text(bot: &Bot, chat_id: i64, text: &str) {
    let _ = bot.send_or_edit(chat_id, text, None, None).await;
}

fn parse_lock_type(arg: &str) -> Option<&'static str> {
    let arg = arg.trim().trim_start_matches('/');
    LOCK_TYPES.iter().copied().find(|t| *t == arg.to_lowercase())
}

/// Returns the first lock type that a message violates (if any).
pub async fn detect_lock_violation(
    client: &Client,
    msg: &Message,
) -> Result<Option<String>, String> {
    let locks = crate::db::locks::list_locks(client, msg.chat.id).await?;
    let locked: Vec<String> = locks
        .iter()
        .filter(|(_, enabled)| *enabled)
        .map(|(t, _)| t.clone())
        .collect();
    if locked.is_empty() {
        return Ok(None);
    }

    if locked.iter().any(|t| t == "photos") && msg.photo.is_some() {
        return Ok(Some("photos".into()));
    }
    if locked.iter().any(|t| t == "videos") && msg.video.is_some() {
        return Ok(Some("videos".into()));
    }
    if locked.iter().any(|t| t == "gifs") && msg.animation.is_some() {
        return Ok(Some("gifs".into()));
    }
    if locked.iter().any(|t| t == "stickers") && msg.sticker.is_some() {
        return Ok(Some("stickers".into()));
    }
    if locked.iter().any(|t| t == "documents") && msg.document.is_some() {
        return Ok(Some("documents".into()));
    }
    if locked.iter().any(|t| t == "voice") && msg.voice.is_some() {
        return Ok(Some("voice".into()));
    }
    if locked.iter().any(|t| t == "audio") && msg.audio.is_some() {
        return Ok(Some("audio".into()));
    }
    if locked.iter().any(|t| t == "video_notes") && msg.video_note.is_some() {
        return Ok(Some("video_notes".into()));
    }
    if locked.iter().any(|t| t == "polls") && msg.poll.is_some() {
        return Ok(Some("polls".into()));
    }
    if locked.iter().any(|t| t == "forward") && msg.forward_date.is_some() {
        return Ok(Some("forward".into()));
    }
    if locked.iter().any(|t| t == "bots") {
        if let Some(members) = &msg.new_chat_members {
            if members.iter().any(|u| u.is_bot) {
                return Ok(Some("bots".into()));
            }
        }
    }
    if locked.iter().any(|t| t == "links") {
        if let Some(text) = msg.text() {
            let has_link = msg.entities().is_some_and(|entities| {
                entities.iter().any(|e: &MessageEntity| {
                    e.type_ == "url" || e.type_ == "text_link" || e.type_ == "email"
                })
            });
            let has_tme = text.contains("t.me/") || text.contains("http://") || text.contains("https://");
            if has_link || has_tme {
                return Ok(Some("links".into()));
            }
        }
    }
    Ok(None)
}

pub async fn handle_lock(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let arg = text.strip_prefix("/lock").unwrap_or("").trim();
    if arg.is_empty() {
        send_text(
            &bot,
            msg.chat.id,
            &format!("Usage: /lock <type>\nAvailable: {}", LOCK_TYPES.join(", ")),
        )
        .await;
        return Ok(());
    }
    let lock = match parse_lock_type(arg) {
        Some(l) => l,
        None => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Unknown lock type '{}'. Available: {}", arg, LOCK_TYPES.join(", ")),
            )
            .await;
            return Ok(());
        }
    };
    let user_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    match crate::db::locks::lock_group(client, msg.chat.id, lock, user_id).await {
        Ok(_) => send_text(&bot, msg.chat.id, &format!("Locked {} 🔒", lock)).await,
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

pub async fn handle_unlock(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let arg = text.strip_prefix("/unlock").unwrap_or("").trim();
    if arg.is_empty() {
        send_text(
            &bot,
            msg.chat.id,
            &format!("Usage: /unlock <type>\nAvailable: {}", LOCK_TYPES.join(", ")),
        )
        .await;
        return Ok(());
    }
    let lock = match parse_lock_type(arg) {
        Some(l) => l,
        None => {
            send_text(
                &bot,
                msg.chat.id,
                &format!("Unknown lock type '{}'. Available: {}", arg, LOCK_TYPES.join(", ")),
            )
            .await;
            return Ok(());
        }
    };
    let user_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    match crate::db::locks::unlock_group(client, msg.chat.id, lock, user_id).await {
        Ok(_) => send_text(&bot, msg.chat.id, &format!("Unlocked {} 🔓", lock)).await,
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

pub async fn handle_locks_list(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match crate::db::locks::list_locks(client, msg.chat.id).await {
        Ok(locks) => {
            if locks.is_empty() {
                send_text(&bot, msg.chat.id, "No locks are active in this group.").await;
            } else {
                let mut text = String::from("*Active locks:*\n");
                for (name, enabled) in &locks {
                    let status = if *enabled { "🔒" } else { "🔓" };
                    text.push_str(&format!("{} {}\n", status, escape_md_v2(name)));
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

use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

use crate::utils::escape_md_v2;

async fn send_text(bot: &Bot, chat_id: i64, text: &str) {
    let _ = bot.send_message(chat_id, text).await;
}

pub async fn handle_setrules(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let text = msg.text().unwrap_or("");
    let rules = text.strip_prefix("/setrules").unwrap_or("").trim();
    if rules.is_empty() {
        send_text(
            &bot,
            msg.chat.id,
            "Usage: /setrules <your group rules>\nExample: /setrules 1. Be kind 2. No spam",
        )
        .await;
        return Ok(());
    }
    let user_id = msg.from().map(|u| u.id as i64).unwrap_or(0);
    match crate::db::rules::set_rules(client, msg.chat.id, rules, user_id).await {
        Ok(_) => send_text(&bot, msg.chat.id, "Group rules saved ✅").await,
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

pub async fn handle_rules(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match crate::db::rules::get_rules(client, msg.chat.id).await {
        Ok(Some(rules)) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!(
                        "*📜 {} rules:*\n\n{}",
                        escape_md_v2(msg.chat.title().unwrap_or("Group")),
                        escape_md_v2(&rules)
                    ),
                )
                .parse_mode(crate::telegram::ParseMode::MarkdownV2)
                .await;
        }
        Ok(None) => {
            send_text(
                &bot,
                msg.chat.id,
                "No rules have been set for this group yet.",
            )
            .await
        }
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

pub async fn handle_clearrules(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match crate::db::rules::clear_rules(client, msg.chat.id).await {
        Ok(true) => send_text(&bot, msg.chat.id, "Group rules cleared.").await,
        Ok(false) => send_text(&bot, msg.chat.id, "No rules were set to clear.").await,
        Err(e) => send_text(&bot, msg.chat.id, &format!("Error: {}", escape_md_v2(&e))).await,
    }
    Ok(())
}

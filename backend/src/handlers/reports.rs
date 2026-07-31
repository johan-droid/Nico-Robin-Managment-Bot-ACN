use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

use crate::utils::escape_md_v2;

/// /report — reply to a message to notify the group's admins.
pub async fn handle_report(bot: Bot, msg: Message, _client: &Client) -> Result<(), String> {
    let reporter = msg
        .from()
        .map(|u| u.username.as_deref().unwrap_or(&u.first_name).to_string())
        .unwrap_or_else(|| "A member".to_string());

    let report_link = msg
        .reply_to_message()
        .map(|r| format!("https://t.me/c/{}/{}", msg.chat.id.to_string().replace("-100", ""), r.id()))
        .unwrap_or_default();

    let text = if report_link.is_empty() {
        format!(
            "⚠️ {} reported a message.\nUse /report by replying to a message to flag it.",
            escape_md_v2(&reporter)
        )
    } else {
        format!(
            "⚠️ {} reported [this message]({}).\nAdmins, please check.",
            escape_md_v2(&reporter),
            report_link
        )
    };

    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(crate::telegram::ParseMode::MarkdownV2)
        .await;

    // Notify admins via DM so the report doesn't get lost.
    if let Ok(admins) = bot.get_chat_administrators(msg.chat.id).await {
        let group = msg.chat.title().unwrap_or("the group");
        for admin in admins {
            let admin_id = admin.user.id;
            if msg.from().is_some_and(|u| u.id == admin_id) {
                continue;
            }
            let _ = bot
                .send_message(
                    admin_id as i64,
                    format!(
                        "⚠️ *Report in {}*\n{} flagged a message for review.\n{}",
                        escape_md_v2(group),
                        escape_md_v2(&reporter),
                        report_link
                    ),
                )
                .parse_mode(crate::telegram::ParseMode::MarkdownV2)
                .await;
        }
    }
    Ok(())
}

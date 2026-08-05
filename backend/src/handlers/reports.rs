use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tokio_postgres::Client;

use crate::utils::escape_md_v2;

/// Per-reporter throttle so a member can't spam /report and flood every admin's
/// private inbox. Keyed by reporter user id, in-memory (fine — resets are safe).
static REPORT_COOLDOWN: std::sync::LazyLock<Mutex<HashMap<i64, Instant>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

const REPORT_COOLDOWN_SECS: u64 = 60;

/// Returns true if the reporter may submit a report now; otherwise false
/// (throttled). Kept as a plain sync fn so the MutexGuard never enters the
/// async state machine (which would make the future non-`Send`).
fn try_acquire_report_slot(reporter_id: i64) -> bool {
    let now = Instant::now();
    if let Ok(mut last) = REPORT_COOLDOWN.lock() {
        if let Some(prev) = last.get(&reporter_id) {
            if now.duration_since(*prev) < Duration::from_secs(REPORT_COOLDOWN_SECS) {
                return false;
            }
        }
        last.insert(reporter_id, now);
    }
    true
}

fn report_link(chat_id: i64, message_id: u64) -> String {
    format!(
        "https://t.me/c/{}/{}",
        chat_id.to_string().replace("-100", ""),
        message_id
    )
}

/// /report — reply to a message to notify the group's admins.
pub async fn handle_report(bot: Bot, msg: Message, _client: &Client) -> Result<(), String> {
    let reporter = msg
        .from()
        .map(|u| u.username.as_deref().unwrap_or(&u.first_name).to_string())
        .unwrap_or_else(|| "A member".to_string());

    let reporter_id = msg.from().map(|u| u.id as i64).unwrap_or(0);

    // Throttle repeated reports per user.
    if !try_acquire_report_slot(reporter_id) {
        let _ = bot
            .send_message(
                msg.chat.id,
                format!(
                    "Please wait {}s before reporting again.",
                    REPORT_COOLDOWN_SECS
                ),
            )
            .await;
        return Ok(());
    }

    let link = msg
        .reply_to_message()
        .map(|r| report_link(msg.chat.id, r.id()));

    let text = match &link {
        Some(l) => format!(
            "⚠️ {} reported [this message]({}).\nAdmins, please check.",
            escape_md_v2(&reporter),
            escape_md_v2(l)
        ),
        None => format!(
            "⚠️ {} reported a message.\nUse /report by replying to a message to flag it.",
            escape_md_v2(&reporter)
        ),
    };

    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(crate::telegram::ParseMode::MarkdownV2)
        .await;

    // Notify admins via DM so the report doesn't get lost. The group title and
    // reporter are escaped; the jump URL is escaped too ('.' is special in
    // MarkdownV2) so the send does not silently fail.
    if let Some(l) = &link {
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
                            "⚠️ *Report in {}*\n{} flagged a message for review.\n[jump to message]({})",
                            escape_md_v2(group),
                            escape_md_v2(&reporter),
                            escape_md_v2(l)
                        ),
                    )
                    .parse_mode(crate::telegram::ParseMode::MarkdownV2)
                    .await;
            }
        }
    }
    Ok(())
}

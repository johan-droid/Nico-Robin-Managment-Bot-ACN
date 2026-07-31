use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use crate::utils::escape_md_v2;

/// /staff — list the group's admins (available to everyone).
pub async fn handle_staff(bot: Bot, msg: Message) -> Result<(), String> {
    if msg.chat.type_ == "private" {
        let _ = bot
            .send_message(
                msg.chat.id,
                "This command only works in groups. Head to a group to see its staff. 👥",
            )
            .await;
        return Ok(());
    }

    let group = escape_md_v2(msg.chat.title().unwrap_or("this group"));
    let admins = match bot.get_chat_administrators(msg.chat.id).await {
        Ok(admins) => admins,
        Err(e) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Failed to fetch staff: {}", escape_md_v2(&e)),
                )
                .await;
            return Ok(());
        }
    };

    let mut lines: Vec<String> = Vec::new();
    for admin in &admins {
        let name = match (&admin.user.username, admin.user.first_name.as_str()) {
            (Some(u), _) => format!("@{}", u),
            (None, f) => f.to_string(),
        };
        let role = match admin.status.as_str() {
            "creator" => "👑 Owner",
            "administrator" => "🛡 Admin",
            _ => "⭐ Moderator",
        };
        lines.push(format!("{} — {}", role, escape_md_v2(&name)));
    }

    if lines.is_empty() {
        let _ = bot.send_message(msg.chat.id, "No admins found.").await;
        return Ok(());
    }

    let text = format!(
        "👑 *Staff of {}*\n✿ ∘ ━━━━━━━━━┉┅╍\n\n{}",
        group,
        lines.join("\n")
    );
    let _ = bot
        .send_message(msg.chat.id, text)
        .parse_mode(crate::telegram::ParseMode::MarkdownV2)
        .await;
    Ok(())
}

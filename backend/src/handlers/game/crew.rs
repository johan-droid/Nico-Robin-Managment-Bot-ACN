use crate::db::games::{
    create_crew, disband_crew, get_crew_bounty, get_crew_by_member, get_crew_leaderboard,
    get_pending_invites, invite_to_crew, join_crew, leave_crew, reject_crew_invite,
};
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;

const CREW_LB_LIMIT: i64 = 10;

pub async fn handle_crew(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    let text_opt = msg.text().unwrap_or("").to_string();
    let parts: Vec<&str> = text_opt.split_whitespace().collect();

    if parts.len() < 2 {
        let text = "⚓ <b>Pirate Crews — Bonds of the Sea</b> ⚓\n✿ ∘ ━━━━━━━━━┉┅╍\n\n\
                    No pirate sails alone, dear. Forge your bonds:\n\n\
                    /crew create &lt;name&gt; — Found a crew and become Captain\n\
                    /crew info — Gaze upon your crew's ledger\n\
                    /crew invite — Reply to someone to extend an invitation\n\
                    /crew invites — Read your pending invitations\n\
                    /crew join &lt;id&gt; — Accept an invitation\n\
                    /crew reject &lt;id&gt; — Decline an invitation\n\
                    /crew leave — Part ways with your crew\n\
                    /crew disband — Scatter the crew to the winds (Captain only)\n\n\
                    ⚠️ A crew's bounty is the sum of all members' bounties.";
        let _ = bot
            .send_message(msg.chat.id, text)
            .parse_mode(crate::telegram::ParseMode::Html)
            .await;
        return Ok(());
    }

    let action = parts[1].to_lowercase();

    match action.as_str() {
        "create" => {
            if parts.len() < 3 {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        "Every great crew needs a name, dear pirate. /crew create <name>",
                    )
                    .await;
                return Ok(());
            }

            // Check if already in a crew
            if let Ok(Some(_)) = get_crew_by_member(client, user_id as i64).await {
                let _ = bot
                    .send_message(msg.chat.id, "Fufufu... you already sail with a crew!")
                    .await;
                return Ok(());
            }

            let name = parts[2..].join(" ");
            match create_crew(client, user_id as i64, &name).await {
                Ok(id) => {
                    let _ = bot
                        .send_message(
                            msg.chat.id,
                            format!(
                                "⚓ Fufufu... the <b>{}</b> has set sail, Captain!\nCrew ID: <code>{}</code>\n\nA bond written into the Wanted Ledger.",
                                name, id
                            ),
                        )
                        .parse_mode(crate::telegram::ParseMode::Html)
                        .await;
                }
                Err(e) => {
                    let _ = bot
                        .send_message(msg.chat.id, format!("Could not create crew: {}", e))
                        .await;
                }
            }
        }
        "info" => match get_crew_by_member(client, user_id as i64).await {
            Ok(Some((id, name, captain_id))) => {
                let bounty = get_crew_bounty(client, id).await.unwrap_or(0);
                let role = if captain_id == (user_id as i64) {
                    "Captain"
                } else {
                    "Crewmate"
                };

                let text = format!(
                        "⚓ <b>{}</b> (ID: <code>{}</code>)\n\nRole: <b>{}</b>\nTotal Crew Bounty: <b>{} Berries</b>\n\nA tale your crew writes together, one wave at a time.",
                        crate::utils::escape_html(&name),
                        id,
                        role,
                        bounty
                    );
                let _ = bot
                    .send_message(msg.chat.id, text)
                    .parse_mode(crate::telegram::ParseMode::Html)
                    .await;
            }
            Ok(None) => {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        "You sail alone, dear pirate. Why not found a crew or join friends?",
                    )
                    .await;
            }
            Err(e) => {
                let _ = bot
                    .send_message(msg.chat.id, format!("Error retrieving crew info: {}", e))
                    .await;
            }
        },
        "invite" => {
            if let Some(reply) = &msg.reply_to_message {
                if let Some(target_user) = reply.from() {
                    if target_user.id == user_id {
                        let _ = bot
                            .send_message(msg.chat.id, "You cannot invite yourself, dear.")
                            .await;
                        return Ok(());
                    }

                    if let Ok(Some((crew_id, name, _captain_id))) =
                        get_crew_by_member(client, user_id as i64).await
                    {
                        // For simplicity, anyone can invite right now
                        match invite_to_crew(client, crew_id, target_user.id as i64, user_id as i64)
                            .await
                        {
                            Ok(_) => {
                                let _ = bot.send_message(
                                    msg.chat.id,
                                    format!("🕊️ An invitation to the <b>{}</b> has been extended to <b>{}</b>.\nThey may accept with /crew join {} or decline with /crew reject {}", crate::utils::escape_html(&name), crate::utils::escape_html(&target_user.first_name), crew_id, crew_id),
                                ).parse_mode(crate::telegram::ParseMode::Html).await;
                            }
                            Err(e) => {
                                let _ = bot
                                    .send_message(
                                        msg.chat.id,
                                        format!("Failed to send invite: {}", e),
                                    )
                                    .await;
                            }
                        }
                    } else {
                        let _ = bot
                            .send_message(msg.chat.id, "You are not in a crew!")
                            .await;
                    }
                } else {
                    let _ = bot
                        .send_message(msg.chat.id, "Could not determine the target user.")
                        .await;
                }
            } else {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        "Please reply to the message of the user you want to invite.",
                    )
                    .await;
            }
        }
        "invites" => match get_pending_invites(client, user_id as i64).await {
            Ok(list) if list.is_empty() => {
                let _ = bot
                    .send_message(msg.chat.id, "You have no pending crew invitations.")
                    .await;
            }
            Ok(list) => {
                let mut text = String::from("📨 <b>Pending Crew Invitations</b>\n✿ ∘ ━━\n");
                for (crew_id, name) in list {
                    text.push_str(&format!(
                        "\n⚓ {} (ID: {})\n   ➕ /crew join {}    ➖ /crew reject {}",
                        crate::utils::escape_html(&name),
                        crew_id,
                        crew_id,
                        crew_id
                    ));
                }
                let _ = bot
                    .send_message(msg.chat.id, text)
                    .parse_mode(crate::telegram::ParseMode::Html)
                    .await;
            }
            Err(e) => {
                let _ = bot
                    .send_message(msg.chat.id, format!("Could not list invites: {}", e))
                    .await;
            }
        },
        "join" => {
            if parts.len() < 3 {
                let _ = bot
                    .send_message(msg.chat.id, "Please specify the Crew ID you want to join!")
                    .await;
                return Ok(());
            }

            if let Ok(crew_id) = parts[2].parse::<i32>() {
                match join_crew(client, user_id as i64, crew_id).await {
                    Ok(_) => {
                        let _ = bot
                            .send_message(
                                msg.chat.id,
                                "Fufufu... welcome aboard, dear pirate. A new bond written in the ledger.",
                            )
                            .await;
                    }
                    Err(e) => {
                        let _ = bot
                            .send_message(msg.chat.id, format!("Failed to join crew: {}", e))
                            .await;
                    }
                }
            } else {
                let _ = bot.send_message(msg.chat.id, "Invalid Crew ID.").await;
            }
        }
        "reject" => {
            if parts.len() < 3 {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        "Please specify the Crew ID you want to reject!",
                    )
                    .await;
                return Ok(());
            }

            if let Ok(crew_id) = parts[2].parse::<i32>() {
                match reject_crew_invite(client, user_id as i64, crew_id).await {
                    Ok(_) => {
                        let _ = bot
                            .send_message(msg.chat.id, "Invitation declined. Safe travels!")
                            .await;
                    }
                    Err(e) => {
                        let _ = bot
                            .send_message(msg.chat.id, format!("Could not reject invite: {}", e))
                            .await;
                    }
                }
            } else {
                let _ = bot.send_message(msg.chat.id, "Invalid Crew ID.").await;
            }
        }
        "leave" => match leave_crew(client, user_id as i64).await {
            Ok(_) => {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        "You have parted ways with the crew, dear. The sea still remembers your name.",
                    )
                    .await;
            }
            Err(e) => {
                let _ = bot.send_message(msg.chat.id, &e).await;
            }
        },
        "disband" => match disband_crew(client, user_id as i64).await {
            Ok(_) => {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        "The crew has been disbanded. The sea remembers...",
                    )
                    .await;
            }
            Err(e) => {
                let _ = bot.send_message(msg.chat.id, &e).await;
            }
        },
        _ => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "Unknown crew action. Valid actions: create, info, invite, invites, join, reject, leave, disband.",
                )
                .await;
        }
    }

    Ok(())
}

pub async fn handle_crew_leaderboard(
    bot: Bot,
    msg: Message,
    client: &Client,
) -> Result<(), String> {
    match get_crew_leaderboard(client, CREW_LB_LIMIT).await {
        Ok(rows) if rows.is_empty() => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "No crew has yet earned a bounty, dear. Found your own with /crew create and write your name in history!",
                )
                .await;
        }
        Ok(rows) => {
            let mut text =
                String::from("🏆 <b>WANTED POSTERS — The Most Infamous Crews</b> 🏆\n✿ ∘ ━━━━\n");
            for (i, (name, bounty)) in rows.iter().enumerate() {
                let medal = match i {
                    0 => "🥇",
                    1 => "🥈",
                    2 => "🥉",
                    _ => "▫️",
                };
                text.push_str(&format!(
                    "\n{} <b>{}</b>\n   💰 {} Berries",
                    medal,
                    crate::utils::escape_html(name),
                    bounty
                ));
            }
            text.push_str("\n\n✿ The World Government has taken notice... Fufufu.");
            let _ = bot
                .send_message(msg.chat.id, text)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        Err(e) => {
            tracing::error!("Error fetching crew leaderboard: {}", e);
            let _ = bot
                .send_message(
                    msg.chat.id,
                    "I couldn't chart the crew leaderboard right now.",
                )
                .await;
        }
    }

    Ok(())
}

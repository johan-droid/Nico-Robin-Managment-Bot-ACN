use tokio_postgres::Client;
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use crate::db::games::{create_crew, get_crew_by_member, get_crew_bounty, invite_to_crew, join_crew, leave_crew};

pub async fn handle_crew(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
    if user_id == 0 {
        return Ok(());
    }

    let text_opt = msg.text().unwrap_or("").to_string();
    let parts: Vec<&str> = text_opt.split_whitespace().collect();

    if parts.len() < 2 {
        let text = "To use the crew system, use these commands:\n\
                    /crew create <name> - Form a new pirate crew\n\
                    /crew info - See your crew's stats\n\
                    /crew invite - Reply to someone to invite them\n\
                    /crew join <id> - Join a crew you've been invited to\n\
                    /crew leave - Leave your current crew";
        let _ = bot.send_message(msg.chat.id, text).await;
        return Ok(());
    }

    let action = parts[1].to_lowercase();

    match action.as_str() {
        "create" => {
            if parts.len() < 3 {
                let _ = bot.send_message(msg.chat.id, "Please specify a crew name!").await;
                return Ok(());
            }

            // Check if already in a crew
            if let Ok(Some(_)) = get_crew_by_member(client, user_id as i64).await {
                let _ = bot.send_message(msg.chat.id, "You are already in a crew!").await;
                return Ok(());
            }

            let name = parts[2..].join(" ");
            match create_crew(client, user_id as i64, &name).await {
                Ok(id) => {
                    let _ = bot.send_message(msg.chat.id, format!("Congratulations, Captain! The *{}* has been formed.\nCrew ID: {}", name, id)).await;
                },
                Err(e) => {
                    let _ = bot.send_message(msg.chat.id, format!("Could not create crew: {}", e)).await;
                }
            }
        },
        "info" => {
            match get_crew_by_member(client, user_id as i64).await {
                Ok(Some((id, name, captain_id))) => {
                    let bounty = get_crew_bounty(client, id).await.unwrap_or(0);
                    let role = if captain_id == (user_id as i64) { "Captain" } else { "Crewmate" };

                    let text = format!("*{}* (ID: {})\n\nRole: {}\nTotal Crew Bounty: *{}* Berries", name, id, role, bounty);
                    let _ = bot.send_message(msg.chat.id, crate::utils::escape_md_v2(&text)).await;
                },
                Ok(None) => {
                    let _ = bot.send_message(msg.chat.id, "You are not currently in a crew. Why not start one or join some friends?").await;
                },
                Err(e) => {
                    let _ = bot.send_message(msg.chat.id, format!("Error retrieving crew info: {}", e)).await;
                }
            }
        },
        "invite" => {
            if let Some(reply) = &msg.reply_to_message {
                if let Some(target_user) = reply.from() {
                    if target_user.id == user_id {
                        let _ = bot.send_message(msg.chat.id, "You cannot invite yourself!").await;
                        return Ok(());
                    }

                    if let Ok(Some((crew_id, name, _captain_id))) = get_crew_by_member(client, user_id as i64).await {
                        // For simplicity, anyone can invite right now
                        match invite_to_crew(client, crew_id, target_user.id as i64, user_id as i64).await {
                            Ok(_) => {
                                let _ = bot.send_message(msg.chat.id, format!("An invitation to join the *{}* has been extended to {}! They can accept by typing /crew join {}", name, target_user.first_name, crew_id)).await;
                            },
                            Err(e) => {
                                let _ = bot.send_message(msg.chat.id, format!("Failed to send invite: {}", e)).await;
                            }
                        }
                    } else {
                        let _ = bot.send_message(msg.chat.id, "You are not in a crew!").await;
                    }
                } else {
                    let _ = bot.send_message(msg.chat.id, "Could not determine the target user.").await;
                }
            } else {
                let _ = bot.send_message(msg.chat.id, "Please reply to the message of the user you want to invite.").await;
            }
        },
        "join" => {
            if parts.len() < 3 {
                let _ = bot.send_message(msg.chat.id, "Please specify the Crew ID you want to join!").await;
                return Ok(());
            }

            if let Ok(crew_id) = parts[2].parse::<i32>() {
                match join_crew(client, user_id as i64, crew_id).await {
                    Ok(_) => {
                        let _ = bot.send_message(msg.chat.id, "Welcome to the crew!").await;
                    },
                    Err(e) => {
                        let _ = bot.send_message(msg.chat.id, format!("Failed to join crew: {}", e)).await;
                    }
                }
            } else {
                let _ = bot.send_message(msg.chat.id, "Invalid Crew ID.").await;
            }
        },
        "leave" => {
            match leave_crew(client, user_id as i64).await {
                Ok(_) => {
                    let _ = bot.send_message(msg.chat.id, "You have successfully left the crew. Safe travels!").await;
                },
                Err(e) => {
                    let _ = bot.send_message(msg.chat.id, &e).await;
                }
            }
        },
        _ => {
            let _ = bot.send_message(msg.chat.id, "Unknown crew action. Valid actions: create, info, invite, join, leave.").await;
        }
    }

    Ok(())
}

pub mod core;
pub mod features;
pub mod federation;
pub mod filters;
pub mod moderation;
pub mod notes;
pub mod profile;
pub mod security;
pub mod welcome;

use std::sync::Arc;

use crate::config::Settings;
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use tokio_postgres::Client;


/// Processes an incoming message. Handles commands, filters, swear checks, and flood detection.
pub async fn handle_message(
    bot: Bot,
    msg: Message,
    state: Arc<super::AppState>,
    client: &Client,
    tracker: &mut crate::auth::flood_tracker::FloodTracker,
    limiter: &mut crate::auth::rate_limiter::RateLimiter,
    flood_settings: Option<(i32, String, i32)>,
    swear_words_cache: &mut Option<Vec<String>>,
) -> Result<(), String> {
    #[cfg(not(target_arch = "wasm32"))]
    sentry::add_breadcrumb(sentry::Breadcrumb {
        category: Some("handler".into()),
        message: Some(format!("Processing message ID {}", msg.message_id)),
        level: sentry::Level::Info,
        ..Default::default()
    });

    let user_id = user_id_from_msg(&msg) as i64;
    let is_admin = crate::auth::is_telegram_admin(&bot, msg.chat.id, user_id as u64).await;

    // Cache the username-to-id mapping if the sender has a username
    if let Some(from) = msg.from() {
        if let Some(ref username) = from.username {
            let lower_username = username.to_lowercase();
            let _ = client.execute(
                "INSERT INTO username_cache (username, user_id, first_name, updated_at) \
                 VALUES ($1, $2, $3, NOW()) \
                 ON CONFLICT (username) DO UPDATE SET user_id = $2, first_name = $3, updated_at = NOW()",
                &[&lower_username, &user_id, &from.first_name],
            ).await;
        }
    }
    // Check if this is an admin replying to a pending username resolution prompt
    if let Some(reply_to) = msg.reply_to_message() {
        if let Some(reply_text) = reply_to.text() {
            if reply_text.starts_with("[Pending] User ") {
                if !is_admin {
                    let _ = bot.send_message(msg.chat.id, "You must be a chat admin to resolve this.").await;
                    return Ok(());
                }
                if let Some(reply_val) = msg.text() {
                    if let Ok(target_id) = reply_val.trim().parse::<i64>() {
                        let parts: Vec<&str> = reply_text.split_whitespace().collect();
                        if parts.len() >= 3 {
                            let username = parts[2].trim_start_matches('@');
                            if let Some(start_idx) = reply_text.find("complete the ") {
                                if let Some(end_idx) = reply_text.find(" command.") {
                                    let command = &reply_text[start_idx + "complete the ".len() .. end_idx];
                                    
                                    // 1. Cache the username -> ID mapping in DB
                                    let lower_username = username.to_lowercase();
                                    let _ = client.execute(
                                        "INSERT INTO username_cache (username, user_id, first_name, updated_at) \
                                         VALUES ($1, $2, $3, NOW()) \
                                         ON CONFLICT (username) DO UPDATE SET user_id = $2, first_name = $3, updated_at = NOW()",
                                        &[&lower_username, &target_id, &username],
                                    ).await;
                                    
                                    tracing::info!(username = %username, target_id = %target_id, command = %command, "Resolved pending username mapping");
                                    
                                    // 2. Build mock message to route the command automatically using the resolved ID
                                    let mut mock_msg = msg.clone();
                                    mock_msg.text = Some(format!("/{} {}", command, target_id));
                                    mock_msg.reply_to_message = None;
                                    
                                    // Call handle_message recursively
                                    return Box::pin(handle_message(
                                        bot,
                                        mock_msg,
                                        state,
                                        client,
                                        tracker,
                                        limiter,
                                        flood_settings,
                                        swear_words_cache,
                                    )).await;
                                }
                            }
                        }
                    } else {
                        let _ = bot.send_message(msg.chat.id, "Invalid User ID. Please reply with a valid numeric ID.").await;
                        return Ok(());
                    }
                }
            }
        }
    }
    // Check if security feature is enabled before checking flood
    let security_enabled = crate::db::features::is_feature_enabled(client, msg.chat.id, "security")
        .await
        .unwrap_or(true);

    if security_enabled && !is_admin {
        if tracker.process_message(&bot, &msg, flood_settings, &state.settings).await {
            return Ok(());
        }
    }

    // Check rate limit for commands
    if msg.text().map_or(false, |t| t.starts_with('/')) && !is_admin {
        match limiter.check(user_id) {
            crate::auth::rate_limiter::RateLimitResult::Denied { retry_after_secs } => {
                let _ = bot
                    .send_message(
                        msg.chat.id,
                        format!("Rate limit exceeded. Please wait {} seconds.", retry_after_secs),
                    )
                    .await;
                return Ok(());
            }
            crate::auth::rate_limiter::RateLimitResult::Allowed => {}
        }
    }

    // Process new chat members (welcome messages)
    if let Some(new_members) = &msg.new_chat_members {
        for member in new_members {
            if member.is_bot && member.id == 0 {
                // Skip self if needed, but we need to know our bot ID
            }
            let _ = welcome::handle_new_member(&bot, &msg, client, member).await;
        }
    }

    // Process left chat members (farewell messages)
    if msg.left_chat_member.is_some() {
        let _ = welcome::handle_left_member(&bot, &msg, client).await;
    }

    // Ensure the group is tracked in the database
    if let Some(title) = msg.chat.title() {
        let _ = crate::db::groups::ensure_group(client, msg.chat.id, title).await;
    }

    // For non-command messages, run filter auto-reply checks and security checks
    if let Some(text) = msg.text() {
        if text.starts_with('/') {
            let mut parts = text.split_whitespace();
            if let Some(mut command) = parts.next() {
                if let Some(idx) = command.find('@') {
                    command = &command[..idx];
                }
                command = command.strip_prefix('/').unwrap_or(command);

                let cmd_name = command.to_lowercase();
                tracing::info!(
                    command = %cmd_name,
                    user_id = %user_id,
                    is_admin = %is_admin,
                    chat_id = %msg.chat.id,
                    "[Command] Received /{} from user {} in chat {}",
                    cmd_name,
                    user_id,
                    msg.chat.id
                );

                match cmd_name.as_str() {
                    "start" => return core::handle_start(bot, msg).await,
                    "help" => return core::handle_help(bot, msg).await,

                    "ban" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_ban(bot, msg, client, &state.settings).await;
                    }
                    "unban" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_unban(bot, msg, client, &state.settings).await;
                    }
                    "kick" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_kick(bot, msg, client, &state.settings).await;
                    }
                    "mute" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_mute(bot, msg, client, &state.settings).await;
                    }
                    "unmute" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_unmute(bot, msg, client, &state.settings).await;
                    }
                    "warn" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_warn(bot, msg, client, &state.settings).await;
                    }
                    "warns" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_warns(bot, msg, client).await;
                    }
                    "resetwarn" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_resetwarn(bot, msg, client, &state.settings)
                            .await;
                    }
                    "slowmode" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_slowmode(bot, msg, &state.settings).await;
                    }
                    "del" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_del(bot, msg, &state.settings).await;
                    }
                    "pin" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "moderation").await? {
                            return Ok(());
                        }
                        return moderation::handle_pin(bot, msg, &state.settings).await;
                    }

                    "save" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "notes").await? {
                            return Ok(());
                        }
                        return notes::handle_save(bot, msg, client).await;
                    }
                    "get" => {
                        if !require_feature(&bot, &msg, client, "notes").await? {
                            return Ok(());
                        }
                        return notes::handle_get(bot, msg, client).await;
                    }
                    "notes" => {
                        if !require_feature(&bot, &msg, client, "notes").await? {
                            return Ok(());
                        }
                        return notes::handle_notes(bot, msg, client).await;
                    }
                    "clear" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "notes").await? {
                            return Ok(());
                        }
                        return notes::handle_clear(bot, msg, client).await;
                    }

                    "filter" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "filters").await? {
                            return Ok(());
                        }
                        return filters::handle_filter(bot, msg, client).await;
                    }
                    "stop" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "filters").await? {
                            return Ok(());
                        }
                        return filters::handle_stop(bot, msg, client).await;
                    }
                    "filters" => {
                        if !require_feature(&bot, &msg, client, "filters").await? {
                            return Ok(());
                        }
                        return filters::handle_filters_list(bot, msg, client).await;
                    }

                    "setwelcome" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_setwelcome(bot, msg, client).await;
                    }
                    "resetwelcome" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_resetwelcome(bot, msg, client).await;
                    }
                    "welcome" => {
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_welcome_preview(bot, msg, client).await;
                    }
                    "setwelcomedm" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_setwelcomedm(bot, msg, client).await;
                    }
                    "setfarewell" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_setfarewell(bot, msg, client).await;
                    }
                    "farewell" => {
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_farewell_preview(bot, msg, client).await;
                    }
                    "cleanwelcome" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_cleanwelcome(bot, msg, client).await;
                    }
                    "welcometest" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "welcome").await? {
                            return Ok(());
                        }
                        return welcome::handle_welcometest(bot, msg, client).await;
                    }

                    "profile" => return profile::handle_profile(bot, msg, client).await,
                    "setbio" => return profile::handle_setbio(bot, msg, client).await,
                    "exportmydata" => return profile::handle_export(bot, msg, client).await,
                    "deletemydata" => return profile::handle_delete_data(bot, msg, client).await,

                    "setflood" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "security").await? {
                            return Ok(());
                        }
                        return security::handle_setflood(bot, msg, client).await;
                    }
                    "flood" => {
                        if !require_feature(&bot, &msg, client, "security").await? {
                            return Ok(());
                        }
                        return security::handle_flood(bot, msg, client).await;
                    }
                    "addswear" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "security").await? {
                            return Ok(());
                        }
                        return security::handle_addswear(bot, msg, client).await;
                    }
                    "delswear" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature(&bot, &msg, client, "security").await? {
                            return Ok(());
                        }
                        return security::handle_delswear(bot, msg, client).await;
                    }

                    "newfed" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return federation::handle_newfed(bot, msg, client).await;
                    }
                    "joinfed" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return federation::handle_joinfed(bot, msg, client).await;
                    }

                    "features" => return features::handle_features_list(bot, msg, client).await,
                    "enable" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return features::handle_enable(bot, msg, client).await;
                    }
                    "disable" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return features::handle_disable(bot, msg, client).await;
                    }
                    "toggle" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return features::handle_toggle(bot, msg, client).await;
                    }
                    "featureinfo" => return features::handle_feature_info(bot, msg).await,
                    "myfeatures" => return features::handle_my_features(bot, msg, client).await,
                    "resetfeatures" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return features::handle_reset_features(bot, msg, client).await;
                    }
                    "enablecategory" | "enable_category" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return features::handle_enable_category(bot, msg, client).await;
                    }
                    "disablecategory" | "disable_category" => {
                        if !require_admin(&bot, &msg).await? {
                            return Ok(());
                        }
                        return features::handle_disable_category(bot, msg, client).await;
                    }
                    _ => return unknown_command(bot, msg).await,
                }
            }
        } else {
            // Non-command message processing:
            // 1. Check filters (auto-reply triggers)
            // 2. Check swear words
            // 3. Flood detection is handled separately via stateful tracker

            // Check if filters feature is enabled before processing
            let filters_enabled = crate::db::features::is_feature_enabled(client, msg.chat.id, "filters")
                .await
                .unwrap_or(true);
            if filters_enabled {
                if let Ok(Some(response)) = crate::db::filters::check_filter(client, msg.chat.id, text).await {
                    let _ = bot.send_message(msg.chat.id, &response).await;
                }
            }

            // Check swear words if security feature is enabled
            let security_enabled = crate::db::features::is_feature_enabled(client, msg.chat.id, "security")
                .await
                .unwrap_or(true);
            if security_enabled {
                let swear_words = match swear_words_cache {
                    Some(list) => list,
                    None => {
                        let list = match client.query("SELECT word FROM swear_words WHERE group_id = $1", &[&msg.chat.id]).await {
                            Ok(rows) => rows.into_iter().map(|r| r.get::<usize, String>(0)).collect::<Vec<_>>(),
                            Err(_) => Vec::new(),
                        };
                        *swear_words_cache = Some(list);
                        swear_words_cache.as_ref().unwrap()
                    }
                };

                let text_lower = text.to_lowercase();
                if let Some(swear) = swear_words.iter().find(|w| text_lower.contains(*w)) {
                    let _ = bot.delete_message(msg.chat.id, msg.id()).await;
                    let _ = bot
                        .send_message(
                            msg.chat.id,
                            format!("Swear word detected: {}", swear),
                        )
                        .await;
                }
            }
        }
    } else {
        // Non-text messages (images, stickers, etc.) - still check filters on caption?
        // For now just run filter check if there's text in caption
        // Telegram doesn't expose caption in our Message struct, so skip
    }

    Ok(())
}

async fn unknown_command(bot: Bot, msg: Message) -> Result<(), String> {
    if msg.chat.is_group() || msg.chat.is_supergroup() {
        return Ok(());
    }
    bot.send_message(
        msg.chat.id,
        "Unknown command. Use /help to see available commands.",
    )
    .await?;
    Ok(())
}

pub async fn log_mod_action(bot: &Bot, settings: &Settings, _chat_id: i64, text: &str) {
    if let Some(log_channel) = settings.log_channel_id {
        let _ = bot.send_message(log_channel, text).await;
    }
}

fn user_id_from_msg(msg: &Message) -> u64 {
    msg.from().map(|u| u.id).unwrap_or(0)
}

async fn require_admin(bot: &Bot, msg: &Message) -> Result<bool, String> {
    let uid = user_id_from_msg(msg);
    tracing::info!(user_id = %uid, chat_id = %msg.chat.id, "Authorizing admin/sudo command executor");

    #[cfg(not(target_arch = "wasm32"))]
    sentry::add_breadcrumb(sentry::Breadcrumb {
        category: Some("auth".into()),
        message: Some(format!("Checking admin permissions for user {}", uid)),
        level: sentry::Level::Info,
        ..Default::default()
    });

    if crate::auth::is_telegram_admin(bot, msg.chat.id, uid).await {
        tracing::info!(user_id = %uid, "Authorization check PASSED");
        Ok(true)
    } else {
        tracing::warn!(user_id = %uid, "Authorization check FAILED (not admin or sudo/privileged user)");
        deny_telegram_admin(bot, msg).await?;
        Ok(false)
    }
}

async fn require_feature(
    bot: &Bot,
    msg: &Message,
    client: &Client,
    feature: &str,
) -> Result<bool, String> {
    let chat_id = msg.chat.id;
    tracing::info!(chat_id = %chat_id, feature = %feature, "Checking feature toggle status");

    #[cfg(not(target_arch = "wasm32"))]
    sentry::add_breadcrumb(sentry::Breadcrumb {
        category: Some("feature".into()),
        message: Some(format!("Checking feature enabled: {}", feature)),
        level: sentry::Level::Info,
        ..Default::default()
    });

    match crate::db::features::is_feature_enabled(client, chat_id, feature).await {
        Ok(true) => {
            tracing::info!(chat_id = %chat_id, feature = %feature, "Feature toggle: ENABLED");
            Ok(true)
        }
        Ok(false) => {
            tracing::warn!(chat_id = %chat_id, feature = %feature, "Feature toggle: DISABLED");
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("The '{}' feature is disabled in this group.", feature),
                )
                .await;
            Ok(false)
        }
        Err(e) => {
            tracing::error!(chat_id = %chat_id, feature = %feature, error = %e, "Feature check error");
            Ok(false)
        }
    }
}

async fn deny_telegram_admin(bot: &Bot, msg: &Message) -> Result<(), String> {
    bot.send_message(msg.chat.id, "You must be a chat admin to use this command.")
        .await?;
    Ok(())
}
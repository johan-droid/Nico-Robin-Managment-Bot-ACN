#![allow(clippy::type_complexity)]
pub mod core;
pub mod features;
pub mod federation;
pub mod filters;
pub mod gbans;
pub mod locks;
pub mod moderation;
pub mod notes;
pub mod profile;
pub mod purge;
pub mod quote;
pub mod reports;
pub mod rules;
pub mod security;
pub mod staff;
pub mod welcome;

use std::collections::HashMap;
use std::sync::Mutex;
use std::time::Instant;

use crate::config::Settings;
use crate::perf;
use crate::perf::LatencyTrace;
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use crate::utils::escape_md_v2;
use tokio_postgres::Client;

// ── In-memory write guards ─────────────────────────────────────────────

/// Tracks last DB-write time per user_id so we skip redundant username_cache upserts.
static USERNAME_CACHE_WRITE_GUARD: std::sync::LazyLock<Mutex<HashMap<i64, Instant>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

/// Tracks last DB-write time per chat_id so we skip redundant group upserts.
static GROUP_WRITE_GUARD: std::sync::LazyLock<Mutex<HashMap<i64, Instant>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

/// In-memory filter cache per group_id with 30-second TTL.
/// Stores (lowercase_trigger, response) pairs so matching avoids per-message allocations.
static FILTER_CACHE: std::sync::LazyLock<Mutex<HashMap<i64, (Vec<(String, String)>, Instant)>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

/// In-memory swear-word cache per group_id with 60-second TTL.
/// Arc so hits clone the word list cheaply without re-querying the DB.
static SWEAR_CACHE: std::sync::LazyLock<
    Mutex<HashMap<i64, (std::sync::Arc<Vec<String>>, Instant)>>,
> = std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

/// Minimum interval between consecutive DB writes for the same user/group.
const CACHE_WRITE_INTERVAL_SECS: u64 = 300; // 5 minutes
/// TTL for in-memory filter cache.
const FILTER_CACHE_TTL_SECS: u64 = 30;
/// TTL for swear-word cache.
const SWEAR_CACHE_TTL_SECS: u64 = 60;

// ── Strict action protocol ────────────────────────────────────────────
/// Maximum warnings before auto-ban.
const MAX_WARNINGS: i64 = 3;

/// Issue a real DB warning and auto-ban if threshold exceeded.
/// Returns (warning_count, was_banned).
pub async fn auto_warn_and_maybe_ban(
    bot: &Bot,
    client: &Client,
    chat_id: i64,
    user_id: i64,
    user_name: &str,
    reason: &str,
) -> (i64, bool) {
    // Respect per-group auto-warn toggle
    if !crate::db::auto_warn::is_auto_warn_enabled(client, chat_id)
        .await
        .unwrap_or(true)
    {
        return (0, false);
    }
    let warned_by: i64 = 0; // system
    let _ = crate::db::warnings::add_warning(client, chat_id, user_id, reason, warned_by).await;
    let count = crate::db::warnings::get_warning_count(client, chat_id, user_id)
        .await
        .unwrap_or(0);

    if count >= MAX_WARNINGS {
        // Permanent ban
        let _ = bot.ban_chat_member(chat_id, user_id as u64).await;
        let _ = bot
            .send_message(
                chat_id,
                format!(
                    "🚫 {} has been permanently banned after {} warnings.\nLast reason: {}",
                    crate::utils::escape_md_v2(user_name),
                    count,
                    crate::utils::escape_md_v2(reason),
                ),
            )
            .await;

        // Notify admins via log channel
        log_mod_action(
            bot,
            Settings::global(),
            chat_id,
            &format!(
                "🚫 Auto-banned {} (exceeded {} warnings) — {}",
                crate::utils::escape_md_v2(user_name),
                MAX_WARNINGS,
                crate::utils::escape_md_v2(reason),
            ),
        )
        .await;

        // Reset warnings after ban
        let _ = crate::db::warnings::reset_warnings(client, chat_id, user_id).await;
        return (count, true);
    }

    (count, false)
}

// ───────────────────────────────────────────────────────────────────────

/// Outcome of the fast security pre-check (flood + rate limit).
#[derive(Debug, PartialEq)]
pub enum SecurityDecision {
    /// Message should be processed normally.
    Proceed,
    FloodAction(crate::auth::flood_tracker::FloodActionInfo),
    RateLimited {
        retry_after_secs: u32,
        user_id: i64,
        user_name: String,
    },
}

pub fn security_precheck_sync(
    msg: &Message,
    is_admin: bool,
    tracker: &mut crate::auth::flood_tracker::FloodTracker,
    limiter: &mut crate::auth::rate_limiter::RateLimiter,
    flood_settings: Option<(i32, String, i32)>,
    security_enabled: bool,
) -> SecurityDecision {
    if is_admin {
        return SecurityDecision::Proceed;
    }
    let user_id = user_id_from_msg(msg);
    let user_name = msg
        .from()
        .as_ref()
        .map(|u| u.username.as_deref().unwrap_or(&u.first_name))
        .unwrap_or("Unknown")
        .to_string();

    if security_enabled {
        if let Some(action) = tracker.evaluate_message(msg, flood_settings) {
            return SecurityDecision::FloodAction(action);
        }
    }

    if msg.text().is_some_and(|t| t.starts_with('/')) {
        match limiter.check(user_id as i64) {
            crate::auth::rate_limiter::RateLimitResult::Denied { retry_after_secs } => {
                return SecurityDecision::RateLimited {
                    retry_after_secs,
                    user_id: user_id as i64,
                    user_name,
                };
            }
            crate::auth::rate_limiter::RateLimitResult::Allowed => {}
        }
    }

    SecurityDecision::Proceed
}

/// Processes an incoming message. Handles commands, filters, swear checks, and flood detection.
pub async fn handle_message(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let user_id = user_id_from_msg(&msg) as i64;
    quote::record_message(client, &msg).await;

    // Run admin check + feature check in parallel — both involve network I/O
    let t_parallel = perf::Timer::start("admin+feature");
    let (is_admin, security_enabled) = tokio::join!(
        async { crate::auth::is_telegram_admin(&bot, msg.chat.id, user_id as u64).await },
        async {
            is_feature_enabled_cached(client, msg.chat.id, "security")
                .await
                .unwrap_or(true)
        }
    );
    LatencyTrace::record("admin+feature", t_parallel.stop());

    // Cache the username-to-id mapping — skip if we wrote within the last 5 minutes
    if let Some(from) = msg.from() {
        if let Some(ref username) = from.username {
            let should_write = USERNAME_CACHE_WRITE_GUARD
                .lock()
                .ok()
                .and_then(|m| m.get(&user_id).copied())
                .map(|ts| ts.elapsed() > std::time::Duration::from_secs(CACHE_WRITE_INTERVAL_SECS))
                .unwrap_or(true);
            if should_write {
                let lower_username = username.to_lowercase();
                let name_enc = crate::crypto::try_encrypt(&from.first_name);
                let _ = client.execute(
                    "INSERT INTO username_cache (username, user_id, first_name, updated_at) \
                     VALUES ($1, $2, $3, NOW()) \
                     ON CONFLICT (username) DO UPDATE SET user_id = $2, first_name = $3, updated_at = NOW()",
                    &[&lower_username, &user_id, &name_enc],
                ).await;
                if let Ok(mut g) = USERNAME_CACHE_WRITE_GUARD.lock() {
                    g.insert(user_id, Instant::now());
                }
            }
        }
    }

    // Check if this is an admin replying to a pending username resolution prompt
    if let Some(reply_to) = msg.reply_to_message() {
        if let Some(reply_text) = reply_to.text() {
            if reply_text.starts_with("[Pending] User ") {
                if !is_admin {
                    let _ = bot
                        .send_message(msg.chat.id, "You must be a chat admin to resolve this.")
                        .await;
                    return Ok(());
                }
                if let Some(reply_val) = msg.text() {
                    if let Ok(target_id) = reply_val.trim().parse::<i64>() {
                        let parts: Vec<&str> = reply_text.split_whitespace().collect();
                        if parts.len() >= 3 {
                            let username = parts[2].trim_start_matches('@');
                            if let Some(start_idx) = reply_text.find("complete the ") {
                                if let Some(end_idx) = reply_text.find(" command.") {
                                    let command =
                                        &reply_text[start_idx + "complete the ".len()..end_idx];

                                    // Cache the resolved username
                                    let lower_username = username.to_lowercase();
                                    let name_enc = crate::crypto::try_encrypt(username);
                                    let _ = client.execute(
                                        "INSERT INTO username_cache (username, user_id, first_name, updated_at) \
                                         VALUES ($1, $2, $3, NOW()) \
                                         ON CONFLICT (username) DO UPDATE SET user_id = $2, first_name = $3, updated_at = NOW()",
                                        &[&lower_username, &target_id, &name_enc],
                                    ).await;

                                    let mut mock_msg = msg.clone();
                                    mock_msg.text = Some(format!("/{} {}", command, target_id));
                                    mock_msg.reply_to_message = None;

                                    return Box::pin(handle_message(bot, mock_msg, client)).await;
                                }
                            }
                        }
                    } else {
                        let _ = bot
                            .send_message(
                                msg.chat.id,
                                "Invalid User ID. Please reply with a valid numeric ID.",
                            )
                            .await;
                        return Ok(());
                    }
                }
            }
        }
    }

    // --- Critical path: security checks ---
    // Group / Chat tracking — skip if we upserted within the last 5 minutes
    let chat_title = msg
        .chat
        .title()
        .map(|s| s.to_string())
        .or_else(|| msg.from().map(|u| u.first_name.clone()))
        .unwrap_or_else(|| "Private Chat".to_string());

    let should_write = GROUP_WRITE_GUARD
        .lock()
        .ok()
        .and_then(|m| m.get(&msg.chat.id).copied())
        .map(|ts| ts.elapsed() > std::time::Duration::from_secs(CACHE_WRITE_INTERVAL_SECS))
        .unwrap_or(true);
    if should_write {
        let _ = crate::db::groups::ensure_group(client, msg.chat.id, &chat_title).await;
        if let Ok(mut g) = GROUP_WRITE_GUARD.lock() {
            g.insert(msg.chat.id, Instant::now());
        }
    }

    let user_name = msg
        .from()
        .as_ref()
        .map(|u| u.username.as_deref().unwrap_or(&u.first_name))
        .unwrap_or("Unknown")
        .to_string();

    // Process new chat members (welcome messages)
    if let Some(new_members) = &msg.new_chat_members {
        let t_welcome = perf::Timer::start("new_member_welcome");
        for member in new_members {
            // Auto-kick globally banned users before they get a welcome.
            if let Ok(Some(_gban)) = crate::db::gbans::get_gban(client, member.id as i64).await {
                let _ = bot.ban_chat_member(msg.chat.id, member.id).await;
                let _ = bot.delete_message(msg.chat.id, msg.id()).await;
                continue;
            }
            let _ = welcome::handle_new_member(&bot, &msg, client, member).await;
        }
        LatencyTrace::record("new_member_welcome", t_welcome.stop());
    }

    // Process left chat members (farewell messages)
    if msg.left_chat_member.is_some() {
        let t_farewell = perf::Timer::start("left_member_farewell");
        let _ = welcome::handle_left_member(&bot, &msg, client).await;
        LatencyTrace::record("left_member_farewell", t_farewell.stop());
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
                    "start" => return core::handle_start(bot, msg, client).await,
                    "help" => return core::handle_help(bot, msg).await,
                    "ban" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_ban(bot, msg, client, Settings::global()).await;
                    }
                    "unban" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_unban(bot, msg, client, Settings::global())
                            .await;
                    }
                    "kick" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_kick(bot, msg, client, Settings::global()).await;
                    }
                    "mute" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_mute(bot, msg, client, Settings::global()).await;
                    }
                    "unmute" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_unmute(bot, msg, client, Settings::global())
                            .await;
                    }
                    "warn" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_warn(bot, msg, client, Settings::global()).await;
                    }
                    "warns" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_warns(bot, msg, client).await;
                    }
                    "resetwarn" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_resetwarn(bot, msg, client, Settings::global())
                            .await;
                    }
                    "slowmode" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_slowmode(bot, msg, Settings::global()).await;
                    }
                    "purge" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return purge::handle_purge(bot, msg, client).await;
                    }
                    "tmute" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_tmute(bot, msg, client, Settings::global())
                            .await;
                    }
                    "tban" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_tban(bot, msg, client, Settings::global()).await;
                    }
                    "kickme" => {
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_kickme(bot, msg, client, Settings::global())
                            .await;
                    }
                    "del" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_del(bot, msg, Settings::global()).await;
                    }
                    "pin" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_pin(bot, msg, Settings::global()).await;
                    }
                    "unpin" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return moderation::handle_unpin(bot, msg, Settings::global()).await;
                    }
                    "staff" => {
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        return staff::handle_staff(bot, msg).await;
                    }

                    "save" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "notes", bot.clone()).await? {
                            return Ok(());
                        }
                        return notes::handle_save(bot, msg, client).await;
                    }
                    "get" => {
                        if !require_feature_fast(client, &msg, "notes", bot.clone()).await? {
                            return Ok(());
                        }
                        return notes::handle_get(bot, msg, client).await;
                    }
                    "notes" => {
                        if !require_feature_fast(client, &msg, "notes", bot.clone()).await? {
                            return Ok(());
                        }
                        return notes::handle_notes(bot, msg, client).await;
                    }
                    "clear" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "notes", bot.clone()).await? {
                            return Ok(());
                        }
                        return notes::handle_clear(bot, msg, client).await;
                    }

                    "setrules" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "rules", bot.clone()).await? {
                            return Ok(());
                        }
                        return rules::handle_setrules(bot, msg, client).await;
                    }
                    "rules" => {
                        if !require_feature_fast(client, &msg, "rules", bot.clone()).await? {
                            return Ok(());
                        }
                        return rules::handle_rules(bot, msg, client).await;
                    }
                    "clearrules" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "rules", bot.clone()).await? {
                            return Ok(());
                        }
                        return rules::handle_clearrules(bot, msg, client).await;
                    }

                    "lock" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "locks", bot.clone()).await? {
                            return Ok(());
                        }
                        return locks::handle_lock(bot, msg, client).await;
                    }
                    "unlock" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "locks", bot.clone()).await? {
                            return Ok(());
                        }
                        return locks::handle_unlock(bot, msg, client).await;
                    }
                    "locks" => {
                        if !require_feature_fast(client, &msg, "locks", bot.clone()).await? {
                            return Ok(());
                        }
                        return locks::handle_locks_list(bot, msg, client).await;
                    }

                    "report" => {
                        if !require_feature_fast(client, &msg, "security", bot.clone()).await? {
                            return Ok(());
                        }
                        return reports::handle_report(bot, msg, client).await;
                    }

                    "gban" => {
                        if !require_sudo_fast(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "federation", bot.clone()).await? {
                            return Ok(());
                        }
                        return gbans::handle_gban(bot, msg, client).await;
                    }
                    "ungban" => {
                        if !require_sudo_fast(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "federation", bot.clone()).await? {
                            return Ok(());
                        }
                        return gbans::handle_ungban(bot, msg, client).await;
                    }
                    "gbans" => {
                        if !require_sudo_fast(&bot, &msg).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "federation", bot.clone()).await? {
                            return Ok(());
                        }
                        return gbans::handle_gbans_list(bot, msg, client).await;
                    }

                    "filter" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "filters", bot.clone()).await? {
                            return Ok(());
                        }
                        return filters::handle_filter(bot, msg, client).await;
                    }
                    "stop" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "filters", bot.clone()).await? {
                            return Ok(());
                        }
                        return filters::handle_stop(bot, msg, client).await;
                    }
                    "filters" => {
                        if !require_feature_fast(client, &msg, "filters", bot.clone()).await? {
                            return Ok(());
                        }
                        return filters::handle_filters_list(bot, msg, client).await;
                    }

                    "setwelcome" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_setwelcome(bot, msg, client).await;
                    }
                    "resetwelcome" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_resetwelcome(bot, msg, client).await;
                    }
                    "welcome" => {
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_welcome_preview(bot, msg, client).await;
                    }
                    "setwelcomedm" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_setwelcomedm(bot, msg, client).await;
                    }
                    "setfarewell" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_setfarewell(bot, msg, client).await;
                    }
                    "farewell" => {
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_farewell_preview(bot, msg, client).await;
                    }
                    "cleanwelcome" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_cleanwelcome(bot, msg, client).await;
                    }
                    "welcometest" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "welcome", bot.clone()).await? {
                            return Ok(());
                        }
                        return welcome::handle_welcometest(bot, msg, client).await;
                    }

                    "profile" => return profile::handle_profile(bot, msg, client).await,
                    "setbio" => return profile::handle_setbio(bot, msg, client).await,
                    "exportmydata" => return profile::handle_export(bot, msg, client).await,
                    "deletemydata" => {
                        if !require_captain_fast(&bot, &msg).await? {
                            return Ok(());
                        }
                        return profile::handle_delete_data(bot, msg, client).await;
                    }
                    "q" => return quote::handle_quote(bot, msg, client).await,
                    cmd if cmd.starts_with('q') && cmd[1..].chars().all(|c| c.is_ascii_digit()) => {
                        return quote::handle_quote(bot, msg, client).await;
                    }

                    "setflood" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "security", bot.clone()).await? {
                            return Ok(());
                        }
                        return security::handle_setflood(bot, msg, client).await;
                    }
                    "flood" => {
                        if !require_feature_fast(client, &msg, "security", bot.clone()).await? {
                            return Ok(());
                        }
                        return security::handle_flood(bot, msg, client).await;
                    }
                    "addswear" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "security", bot.clone()).await? {
                            return Ok(());
                        }
                        return security::handle_addswear(bot, msg, client).await;
                    }
                    "delswear" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "security", bot.clone()).await? {
                            return Ok(());
                        }
                        return security::handle_delswear(bot, msg, client).await;
                    }

                    "autowarnon" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        let _ = crate::db::auto_warn::enable_auto_warn(client, msg.chat.id).await;
                        let _ = bot
                            .send_message(msg.chat.id, "Auto-warn has been enabled ✅")
                            .await;
                    }
                    "autowarnoff" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        if !require_feature_fast(client, &msg, "moderation", bot.clone()).await? {
                            return Ok(());
                        }
                        let _ = crate::db::auto_warn::disable_auto_warn(client, msg.chat.id).await;
                        let _ = bot
                            .send_message(msg.chat.id, "Auto-warn has been disabled ❌")
                            .await;
                    }

                    "newfed" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return federation::handle_newfed(bot, msg, client).await;
                    }
                    "joinfed" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return federation::handle_joinfed(bot, msg, client).await;
                    }

                    "features" => return features::handle_features_list(bot, msg, client).await,
                    "enable" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return features::handle_enable(bot, msg, client).await;
                    }
                    "disable" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return features::handle_disable(bot, msg, client).await;
                    }
                    "toggle" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return features::handle_toggle(bot, msg, client).await;
                    }
                    "featureinfo" => return features::handle_feature_info(bot, msg).await,
                    "myfeatures" => return features::handle_my_features(bot, msg, client).await,
                    "resetfeatures" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return features::handle_reset_features(bot, msg, client).await;
                    }
                    "enablecategory" | "enable_category" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return features::handle_enable_category(bot, msg, client).await;
                    }
                    "disablecategory" | "disable_category" => {
                        if !require_admin_fast(&bot, &msg, is_admin).await? {
                            return Ok(());
                        }
                        return features::handle_disable_category(bot, msg, client).await;
                    }
                    _ => return unknown_command(bot, msg).await,
                }
            }
        } else {
            // Non-command message processing

            // Check lock enforcement (locks feature must be enabled for the group)
            if !is_admin {
                let locks_enabled = is_feature_enabled_cached(client, msg.chat.id, "locks")
                    .await
                    .unwrap_or(true);
                if locks_enabled {
                    if let Ok(Some(lock_type)) = locks::detect_lock_violation(client, &msg).await {
                        let _ = bot.delete_message(msg.chat.id, msg.id()).await;
                        let offender = msg
                            .from()
                            .map(|u| u.username.as_deref().unwrap_or(&u.first_name).to_string())
                            .unwrap_or_else(|| "A member".to_string());
                        let _ = bot
                            .send_message(
                                msg.chat.id,
                                format!(
                                    "🔒 {} is locked here — your message was removed.",
                                    lock_type
                                ),
                            )
                            .await;
                        let _ = crate::handlers::log_mod_action(
                            &bot,
                            Settings::global(),
                            msg.chat.id,
                            &format!(
                                "Deleted locked content ({}) from {} in {}",
                                lock_type,
                                escape_md_v2(&offender),
                                escape_md_v2(msg.chat.title().unwrap_or("group"))
                            ),
                        )
                        .await;
                        return Ok(());
                    }
                }
            }

            let text_lower = text.to_lowercase();

            // Check if filters feature is enabled before processing
            let filters_enabled = is_feature_enabled_cached(client, msg.chat.id, "filters")
                .await
                .unwrap_or(true);
            if filters_enabled {
                // In-memory filter cache with 30s TTL — avoids full table scan per message.
                // Triggers are pre-lowercased once at cache time so matching never allocates.
                let cached: Option<(Vec<(String, String)>, Instant)> = FILTER_CACHE
                    .lock()
                    .ok()
                    .and_then(|m| m.get(&msg.chat.id).cloned())
                    .filter(|(_, ts)| {
                        ts.elapsed() < std::time::Duration::from_secs(FILTER_CACHE_TTL_SECS)
                    });
                let filters = if let Some((list, _)) = cached {
                    list
                } else {
                    let list = crate::db::filters::list_filters(client, msg.chat.id)
                        .await
                        .unwrap_or_default()
                        .into_iter()
                        .map(|f| (f.trigger_text.to_lowercase(), f.response))
                        .collect::<Vec<_>>();
                    if let Ok(mut m) = FILTER_CACHE.lock() {
                        m.insert(msg.chat.id, (list.clone(), Instant::now()));
                    }
                    list
                };
                if let Some((_, response)) = filters
                    .iter()
                    .find(|(trigger, _)| text_lower.contains(trigger))
                {
                    let _ = bot.send_message(msg.chat.id, response).await;
                }
            }

            // Check swear words if security feature is enabled (in-memory 60s TTL)
            if security_enabled {
                let swear_words = {
                    let mut cached: Option<std::sync::Arc<Vec<String>>> = None;
                    if let Ok(cache) = SWEAR_CACHE.lock() {
                        if let Some((words, ts)) = cache.get(&msg.chat.id) {
                            if ts.elapsed() < std::time::Duration::from_secs(SWEAR_CACHE_TTL_SECS) {
                                cached = Some(std::sync::Arc::clone(words));
                            }
                        }
                    }
                    match cached {
                        Some(words) => words,
                        None => {
                            let list = match client
                                .query(
                                    "SELECT word FROM swear_words WHERE group_id = $1",
                                    &[&msg.chat.id],
                                )
                                .await
                            {
                                Ok(rows) => rows
                                    .into_iter()
                                    .map(|r| r.get::<usize, String>(0))
                                    .collect::<Vec<_>>(),
                                Err(_) => Vec::new(),
                            };
                            let words = std::sync::Arc::new(list);
                            if let Ok(mut cache) = SWEAR_CACHE.lock() {
                                cache.insert(
                                    msg.chat.id,
                                    (std::sync::Arc::clone(&words), Instant::now()),
                                );
                            }
                            words
                        }
                    }
                };

                if let Some(swear) = swear_words.iter().find(|w| text_lower.contains(*w)) {
                    let _ = bot.delete_message(msg.chat.id, msg.id()).await;
                    let _ = bot
                        .send_message(msg.chat.id, format!("Swear word detected: {}", swear))
                        .await;
                    auto_warn_and_maybe_ban(
                        &bot,
                        client,
                        msg.chat.id,
                        user_id,
                        &user_name,
                        &format!("swear word: {}", swear),
                    )
                    .await;
                }
            }
        }
    }

    Ok(())
}

async fn unknown_command(_bot: Bot, msg: Message) -> Result<(), String> {
    tracing::debug!(command = %msg.text().unwrap_or(""), "Unknown command ignored");
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

/// Fast path: uses is_admin already computed at the top of handle_message.
async fn require_admin_fast(bot: &Bot, msg: &Message, is_admin: bool) -> Result<bool, String> {
    if is_admin {
        Ok(true)
    } else {
        deny_telegram_admin(bot, msg).await?;
        Ok(false)
    }
}

/// Fast path: checks if user is a bot operator (SUDO_USERS / CAPTAIN_ID / COMMANDER_IDS).
async fn require_sudo_fast(bot: &Bot, msg: &Message) -> Result<bool, String> {
    let user_id = user_id_from_msg(msg);
    if crate::auth::is_sudo_or_privileged(user_id) {
        Ok(true)
    } else {
        let _ = bot
            .send_message(msg.chat.id, "This command is restricted to bot operators.")
            .await;
        Ok(false)
    }
}

/// Requires the user to be the group captain (creator/owner) or a developer.
async fn require_captain_fast(bot: &Bot, msg: &Message) -> Result<bool, String> {
    let user_id = user_id_from_msg(msg);
    if crate::auth::is_captain_or_developer(bot, msg.chat.id, user_id).await {
        Ok(true)
    } else {
        let _ = bot
            .send_message(
                msg.chat.id,
                "Only the group captain (owner) or a developer can delete data.",
            )
            .await;
        Ok(false)
    }
}

/// Fast path: uses in-memory feature cache and only hits DB on cache miss.
async fn require_feature_fast(
    client: &Client,
    msg: &Message,
    feature: &str,
    _bot: Bot,
) -> Result<bool, String> {
    // Features are always enabled in private chats (no DB records exist for them)
    if !msg.chat.is_group() && !msg.chat.is_supergroup() {
        return Ok(true);
    }
    let enabled = is_feature_enabled_cached(client, msg.chat.id, feature)
        .await
        .unwrap_or(true);
    if enabled {
        Ok(true)
    } else {
        tracing::debug!(feature = %feature, "Feature disabled for group, command blocked");
        Ok(false)
    }
}

/// Feature check with in-memory caching (30s TTL).
pub async fn is_feature_enabled_cached(
    client: &Client,
    chat_id: i64,
    feature: &str,
) -> Result<bool, String> {
    if chat_id > 0 {
        return Ok(true);
    }
    if let Some(cached) = crate::db::feature_cache::get_cached(chat_id, feature) {
        return Ok(cached);
    }
    let result = crate::db::features::is_feature_enabled(client, chat_id, feature).await;
    if let Ok(enabled) = result {
        crate::db::feature_cache::set_cached(chat_id, feature, enabled);
    }
    result
}

async fn deny_telegram_admin(bot: &Bot, msg: &Message) -> Result<(), String> {
    tracing::debug!(chat_id = %msg.chat.id, "Non-admin tried to use admin command, blocked");
    let _ = bot
        .send_message(
            msg.chat.id,
            "⚠️ Permission denied: This command requires group administrator privileges.",
        )
        .await;
    Ok(())
}

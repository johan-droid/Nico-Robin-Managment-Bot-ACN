pub mod core;
pub mod moderation;
pub mod notes;
pub mod filters;
pub mod welcome;
pub mod profile;
pub mod security;
pub mod federation;
pub mod features;

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use sqlx::PgPool;
use teloxide::dispatching::UpdateHandler;
use teloxide::dptree;
use teloxide::macros::BotCommands;
use teloxide::prelude::*;
use teloxide::types::Update;
use crate::auth;
use crate::config::Settings;
use crate::db;

#[derive(BotCommands, Clone)]
#[command(rename_rule = "lowercase", description = "Nico Robin Bot commands")]
pub enum Command {
    Start,
    Help,

    Ban,
    Unban,
    Kick,
    Mute,
    Unmute,
    Warn,
    Warns,
    Resetwarn,
    Slowmode,
    Del,
    Pin,

    Save,
    Get,
    Notes,
    Clear,

    Filter,
    Stop,
    Filters,

    Setwelcome,
    Resetwelcome,
    Welcome,
    Setwelcomedm,
    Setfarewell,
    Farewell,
    Cleanwelcome,
    Welcometest,

    Profile,
    Setbio,
    ExportMyData,
    DeleteMyData,

    Setflood,
    Flood,
    Addswear,
    Delswear,

    Newfed,
    Joinfed,

    Features,
    Enable,
    Disable,
    Toggle,
    FeatureInfo,
    MyFeatures,
    ResetFeatures,
    EnableCategory,
    DisableCategory,
}

pub type FilterCache = Arc<RwLock<HashMap<i64, HashMap<String, String>>>>;
pub type SwearCache = Arc<RwLock<HashMap<i64, Vec<String>>>>;
pub type GroupCache = Arc<RwLock<std::collections::HashSet<i64>>>;
pub type LastWelcomeCache = Arc<RwLock<HashMap<i64, teloxide::types::MessageId>>>;

/// Shared app state passed to handlers.
#[derive(Clone)]
pub struct AppState {
    pub settings: Arc<Settings>,
    pub pool: PgPool,
    pub filter_cache: FilterCache,
    pub swear_cache: SwearCache,
    pub rate_limiter: auth::rate_limiter::SharedRateLimiter,
    pub flood_tracker: auth::flood_tracker::SharedFloodTracker,
    pub group_cache: GroupCache,
    pub last_welcome_cache: LastWelcomeCache,
}

/// Builds the full handler tree: commands, welcome/farewell events, and filter triggers.
pub fn build_handler(state: Arc<AppState>) -> UpdateHandler<teloxide::RequestError> {
    let state_for_cmd = state.clone();
    let state_for_join = state.clone();
    let state_for_leave = state.clone();

    dptree::entry()
        .branch(
            Update::filter_message()
                .filter_command::<Command>()
                .endpoint({
                    move |bot: Bot, msg: Message, cmd: Command| {
                        let state = state_for_cmd.clone();
                        async move { handle_command(bot, msg, cmd, state).await }
                    }
                }),
        )
        .branch(
            Update::filter_message()
                .filter(|msg: Message| {
                    msg.text()
                        .map(|t| t.starts_with('/'))
                        .unwrap_or(false)
                })
                .endpoint(unknown_command),
        )
        .branch(
            Update::filter_message()
                .filter(|msg: Message| msg.new_chat_members().is_some())
                .endpoint({
                    move |bot: Bot, msg: Message| {
                        let state = state_for_join.clone();
                        async move { handle_new_chat_members(bot, msg, &state).await }
                    }
                }),
        )
        .branch(
            Update::filter_message()
                .filter(|msg: Message| msg.left_chat_member().is_some())
                .endpoint({
                    move |bot: Bot, msg: Message| {
                        let state = state_for_leave.clone();
                        async move { handle_left_chat_member(bot, msg, &state).await }
                    }
                }),
        )
        .map(move |msg: Message, bot: Bot| {
            let state = state.clone();
            tokio::spawn(async move {
                handle_filters_trigger(bot, msg, &state).await;
            });
        })
}

/// Sends a welcome message when a new member joins.
async fn handle_new_chat_members(
    bot: Bot,
    msg: Message,
    state: &AppState,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    let members = match msg.new_chat_members() {
        Some(m) => m,
        None => return Ok(()),
    };

    let settings = match db::welcome::get_welcome_settings(&state.pool, chat_id).await {
        Ok(Some(s)) => s,
        _ => return Ok(()),
    };

    let welcome_template = match settings.welcome_message {
        Some(t) if !t.is_empty() => t,
        _ => return Ok(()),
    };

    let group_name = msg.chat.title().unwrap_or("this group");
    let member_count = bot
        .get_chat_member_count(msg.chat.id)
        .await
        .map(|c| c.to_string())
        .unwrap_or_else(|_| "N/A".to_string());

    for member in members {
        let user_name = member.first_name.as_str();
        let welcome = welcome_template
            .replace("{user}", user_name)
            .replace("{group}", group_name)
            .replace("{count}", &member_count);

        if settings.clean_welcome {
            let old_msg_id = state.last_welcome_cache.write().await.remove(&chat_id);
            if let Some(old_id) = old_msg_id {
                let _ = bot.delete_message(msg.chat.id, old_id).await;
            }
        }

        if let Ok(sent_msg) = bot.send_message(msg.chat.id, &welcome).await {
            if settings.clean_welcome {
                state.last_welcome_cache.write().await.insert(chat_id, sent_msg.id);
            }
        }

        if let Some(dm_template) = &settings.welcome_dm_message {
            if !dm_template.is_empty() {
                let dm = dm_template
                    .replace("{user}", user_name)
                    .replace("{group}", group_name)
                    .replace("{count}", &member_count);
                let _ = bot.send_message(UserId(member.id.0), &dm).await;
            }
        }
    }

    Ok(())
}

/// Sends a farewell message when a member leaves.
async fn handle_left_chat_member(
    bot: Bot,
    msg: Message,
    state: &AppState,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    let member = match msg.left_chat_member() {
        Some(m) => m,
        None => return Ok(()),
    };

    let settings = match db::welcome::get_welcome_settings(&state.pool, chat_id).await {
        Ok(Some(s)) => s,
        _ => return Ok(()),
    };

    let farewell_template = match settings.farewell_message {
        Some(t) if !t.is_empty() => t,
        _ => return Ok(()),
    };

    let group_name = msg.chat.title().unwrap_or("this group");
    let farewell = farewell_template
        .replace("{user}", member.first_name.as_str())
        .replace("{group}", group_name);

    let _ = bot.send_message(msg.chat.id, &farewell).await;
    Ok(())
}

/// Main command dispatcher.
async fn handle_command(
    bot: Bot,
    msg: Message,
    cmd: Command,
    state: Arc<AppState>,
) -> Result<(), teloxide::RequestError> {
    let settings = &state.settings;
    let pool = &state.pool;
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let chat_id = msg.chat.id;

    // Rate limiting check (per-user-per-group and global)
    if let auth::rate_limiter::RateLimitResult::Denied { retry_after_secs } =
        state.rate_limiter.check(user_id, chat_id.0 as i64, settings).await
    {
        let _ = bot
            .send_message(
                chat_id,
                format!("⚠️ You are sending commands too quickly. Please wait {} seconds.", retry_after_secs),
            )
            .await;
        return Ok(());
    }

    // Enforce allowed_group_ids when the list is non-empty
    if !settings.allowed_group_ids.is_empty()
        && !settings.allowed_group_ids.contains(&(chat_id.0 as i64))
        && (msg.chat.is_group() || msg.chat.is_supergroup())
    {
        return Ok(());
    }

    if let Some(title) = msg.chat.title() {
        let is_cached = {
            let cache = state.group_cache.read().await;
            cache.contains(&(chat_id.0 as i64))
        };
        if !is_cached {
            if db::groups::ensure_group(pool, chat_id.0 as i64, title).await.is_ok() {
                state.group_cache.write().await.insert(chat_id.0 as i64);
            }
        }
    }

    match cmd {
        Command::Start => core::handle_start(bot, msg).await,
        Command::Help => core::handle_help(bot, msg).await,

        Command::Ban => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_ban(bot, msg, settings).await
        }
        Command::Unban => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_unban(bot, msg, settings).await
        }
        Command::Kick => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_kick(bot, msg, settings).await
        }
        Command::Mute => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_mute(bot, msg, settings).await
        }
        Command::Unmute => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_unmute(bot, msg, settings).await
        }
        Command::Warn => {
            require_commander(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_warn(bot, msg, pool, settings).await
        }
        Command::Warns => {
            require_commander(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_warns(bot, msg, pool).await
        }
        Command::Resetwarn => {
            require_commander(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_resetwarn(bot, msg, pool, settings).await
        }
        Command::Slowmode => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_slowmode(bot, msg, settings).await
        }
        Command::Del => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_del(bot, msg, settings).await
        }
        Command::Pin => {
            require_commander_with_admin(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "moderation").await?;
            moderation::handle_pin(bot, msg, settings).await
        }

        Command::Save => {
            require_commander(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "notes").await?;
            notes::handle_save(bot, msg, pool).await
        }
        Command::Get => {
            require_feature(&bot, &msg, pool, "notes").await?;
            notes::handle_get(bot, msg, pool).await
        }
        Command::Notes => {
            require_feature(&bot, &msg, pool, "notes").await?;
            notes::handle_notes(bot, msg, pool).await
        }
        Command::Clear => {
            require_commander(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "notes").await?;
            notes::handle_clear(bot, msg, pool).await
        }

        Command::Filter => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "filters").await?;
            filters::handle_filter(bot, msg, pool, &state.filter_cache).await
        }
        Command::Stop => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "filters").await?;
            filters::handle_stop(bot, msg, pool, &state.filter_cache).await
        }
        Command::Filters => {
            require_feature(&bot, &msg, pool, "filters").await?;
            filters::handle_filters_list(bot, msg, pool).await
        }

        Command::Setwelcome => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_setwelcome(bot, msg, pool).await
        }
        Command::Resetwelcome => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_resetwelcome(bot, msg, pool).await
        }
        Command::Welcome => {
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_welcome_preview(bot, msg, pool).await
        }
        Command::Setwelcomedm => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_setwelcomedm(bot, msg, pool).await
        }
        Command::Setfarewell => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_setfarewell(bot, msg, pool).await
        }
        Command::Farewell => {
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_farewell_preview(bot, msg, pool).await
        }
        Command::Cleanwelcome => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_cleanwelcome(bot, msg, pool).await
        }
        Command::Welcometest => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "welcome").await?;
            welcome::handle_welcometest(bot, msg, pool).await
        }

        Command::Profile => profile::handle_profile(bot, msg, pool).await,
        Command::Setbio => profile::handle_setbio(bot, msg, pool).await,
        Command::ExportMyData => profile::handle_export(bot, msg, pool).await,
        Command::DeleteMyData => profile::handle_delete_data(bot, msg, pool).await,

        Command::Setflood => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "security").await?;
            security::handle_setflood(bot, msg, pool).await
        }
        Command::Flood => {
            require_feature(&bot, &msg, pool, "security").await?;
            security::handle_flood(bot, msg, pool).await
        }
        Command::Addswear => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "security").await?;
            security::handle_addswear(bot, msg, pool, &state.swear_cache).await
        }
        Command::Delswear => {
            require_captain(&bot, &msg, user_id, settings).await?;
            require_feature(&bot, &msg, pool, "security").await?;
            security::handle_delswear(bot, msg, pool, &state.swear_cache).await
        }

        Command::Newfed => {
            require_sudo(&bot, &msg, user_id, settings).await?;
            federation::handle_newfed(bot, msg, pool).await
        }
        Command::Joinfed => {
            require_sudo(&bot, &msg, user_id, settings).await?;
            federation::handle_joinfed(bot, msg, pool).await
        }

        Command::Features => features::handle_features_list(bot, msg, pool).await,
        Command::Enable => {
            require_captain(&bot, &msg, user_id, settings).await?;
            features::handle_enable(bot, msg, pool).await
        }
        Command::Disable => {
            require_captain(&bot, &msg, user_id, settings).await?;
            features::handle_disable(bot, msg, pool).await
        }
        Command::Toggle => {
            require_captain(&bot, &msg, user_id, settings).await?;
            features::handle_toggle(bot, msg, pool).await
        }
        Command::FeatureInfo => features::handle_feature_info(bot, msg).await,
        Command::MyFeatures => features::handle_my_features(bot, msg, pool).await,
        Command::ResetFeatures => {
            require_captain(&bot, &msg, user_id, settings).await?;
            features::handle_reset_features(bot, msg, pool).await
        }
        Command::EnableCategory => {
            require_captain(&bot, &msg, user_id, settings).await?;
            features::handle_enable_category(bot, msg, pool).await
        }
        Command::DisableCategory => {
            require_captain(&bot, &msg, user_id, settings).await?;
            features::handle_disable_category(bot, msg, pool).await
        }
    }
}

async fn unknown_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
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

async fn handle_filters_trigger(bot: Bot, msg: Message, state: &AppState) {
    if state
        .flood_tracker
        .process_message(&bot, &msg, &state.pool, &state.settings)
        .await
    {
        return;
    }

    let text = match msg.text() {
        Some(t) => t,
        None => return,
    };
    let chat_id = msg.chat.id.0 as i64;
    let lower = text.to_lowercase();

    // Check filters cache (substring / contains matching)
    {
        let cache = state.filter_cache.read().await;
        if let Some(group_filters) = cache.get(&chat_id) {
            for (trigger, response) in group_filters {
                if lower.contains(&trigger.to_lowercase()) {
                    let _ = bot.send_message(msg.chat.id, response).await;
                    return;
                }
            }
        }
    }

    // Check swears cache
    {
        let cache = state.swear_cache.read().await;
        if let Some(group_swears) = cache.get(&chat_id) {
            if group_swears.iter().any(|w| lower.contains(w.as_str())) {
                let _ = bot.delete_message(msg.chat.id, msg.id).await;
            }
        }
    }
}

/// Logs a moderation action to the configured log channel, if set.
pub async fn log_mod_action(bot: &Bot, settings: &Settings, _chat_id: ChatId, text: &str) {
    if let Some(log_channel) = settings.log_channel_id {
        let _ = bot.send_message(ChatId(log_channel), text).await;
    }
}

fn user_id_from_msg(msg: &Message) -> UserId {
    msg.from()
        .map(|u| u.id)
        .unwrap_or(UserId(0))
}

async fn require_commander(
    bot: &Bot,
    msg: &Message,
    _user_id: i64,
    _settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    // Check if user is a Telegram group admin (owner or administrator)
    if !auth::is_telegram_admin(bot, msg.chat.id, user_id_from_msg(msg)).await {
        return deny_telegram_admin(bot, msg).await;
    }
    Ok(())
}

async fn require_commander_with_admin(
    bot: &Bot,
    msg: &Message,
    _user_id: i64,
    _settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    // Check if user is a Telegram group admin (owner or administrator)
    if !auth::is_telegram_admin(bot, msg.chat.id, user_id_from_msg(msg)).await {
        return deny_telegram_admin(bot, msg).await;
    }
    Ok(())
}

async fn require_captain(
    bot: &Bot,
    msg: &Message,
    _user_id: i64,
    _settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    // Check if user is a Telegram group admin (owner or administrator)
    if !auth::is_telegram_admin(bot, msg.chat.id, user_id_from_msg(msg)).await {
        return deny_telegram_admin(bot, msg).await;
    }
    Ok(())
}

async fn require_sudo(
    bot: &Bot,
    msg: &Message,
    _user_id: i64,
    _settings: &Settings,
) -> Result<(), teloxide::RequestError> {
    // Check if user is a Telegram group admin (owner or administrator)
    if !auth::is_telegram_admin(bot, msg.chat.id, user_id_from_msg(msg)).await {
        return deny_telegram_admin(bot, msg).await;
    }
    Ok(())
}

async fn require_feature(
    bot: &Bot,
    msg: &Message,
    pool: &PgPool,
    feature: &str,
) -> Result<(), teloxide::RequestError> {
    let chat_id = msg.chat.id.0 as i64;
    match db::features::is_feature_enabled(pool, chat_id, feature).await {
        Ok(true) => Ok(()),
        Ok(false) => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("The '{}' feature is disabled in this group.", feature),
                )
                .await;
            Ok(())
        }
        Err(_) => Ok(()),
    }
}

async fn deny_telegram_admin(
    bot: &Bot,
    msg: &Message,
) -> Result<(), teloxide::RequestError> {
    bot.send_message(
        msg.chat.id,
        "You must be a chat admin to use this command.",
    )
    .await?;
    Ok(())
}

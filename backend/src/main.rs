mod auth;
mod config;
mod entities;
mod utils;

use std::fmt;
use std::net::SocketAddr;
use std::sync::Arc;

use auth::rate_limiter::RateLimiter;
use auth::validator::InputValidator;
use axum::extract::State;
use axum::http::{HeaderMap, StatusCode};
use axum::routing::{get, post};
use axum::{Json, Router};
use config::Settings;
use entities::{establish_connection, verify_database};
use teloxide::dispatching::UpdateHandler;
use teloxide::dptree;
use teloxide::macros::BotCommands;
use teloxide::prelude::*;
use teloxide::types::Update;
use teloxide::Bot;
use tower_http::cors::CorsLayer;
use tower_http::limit::RequestBodyLimitLayer;
use tower_http::trace::TraceLayer;
use tracing::{error, info, warn};
use utils::logging::configure_logging;

/// Bot commands supported by the dispatcher.
#[derive(BotCommands, Clone)]
#[command(rename_rule = "lowercase", description = "Nico Robin Bot commands")]
enum Command {
    #[command(description = "Start the bot")]
    Start,
    #[command(description = "Show help message")]
    Help,
}

impl fmt::Display for Command {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Command::Start => write!(f, "/start"),
            Command::Help => write!(f, "/help"),
        }
    }
}

fn log_robin_banner() {
    let banner = "  /\\_/\\ | ( .. )  Nico Robin Bot | / > < \\  Rust backend ready";
    tracing::info!(banner = banner, "robin_ready_banner");
}

/// Shared application state.
#[derive(Clone)]
#[allow(dead_code)]
struct AppState {
    settings: Arc<Settings>,
    bot: Bot,
    rate_limiter: Arc<RateLimiter>,
    webhook_secret: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Load configuration
    let settings = Settings::load().map_err(|e| {
        eprintln!("Failed to load configuration settings: {e:?}");
        e
    })?;

    // Initialize logging
    configure_logging(&settings.log_level, &settings.environment);
    log_robin_banner();

    // Initialize database connection pool with retry logic
    let db_pool = establish_connection(&settings).await.map_err(|e| {
        error!(error = ?e, "database_connection_failed");
        e
    })?;

    // Verify database connection
    verify_database(&db_pool).await.map_err(|e| {
        error!(error = ?e, "database_verification_failed");
        e
    })?;

    // Initialize Telegram Bot
    let bot = Bot::new(settings.bot_token.clone());
    info!("telegram_bot_initialized");

    // Initialize rate limiter
    let rate_limiter = Arc::new(RateLimiter::new());
    info!("rate_limiter_initialized");

    // Build shared state
    let state = AppState {
        settings: Arc::new(settings.clone()),
        bot: bot.clone(),
        rate_limiter,
        webhook_secret: settings.webhook_secret.clone(),
    };

    // Start based on bot mode
    match settings.bot_mode.as_str() {
        "polling" => {
            info!("starting_bot_in_polling_mode");
            let handler = build_handler();
            run_polling_dispatcher(bot, handler).await;
        }
        "webhook" | "auto" => {
            info!("starting_bot_in_webhook_mode");
            // Start the HTTP server
            let server = start_http_server(state.clone(), &settings).await?;

            // Build and run the webhook dispatcher
            let handler = build_handler();

            // Run both the HTTP server and bot dispatcher
            let _ = tokio::join!(server, run_webhook_dispatcher(bot, handler, &settings),);
        }
        _ => {
            error!(mode = settings.bot_mode, "unknown_bot_mode");
            std::process::exit(1);
        }
    }

    info!("Nico Robin Bot Rust backend initialized successfully in backend/!");
    Ok(())
}

/// Starts the HTTP server for webhook reception and health checks.
async fn start_http_server(
    state: AppState,
    settings: &Settings,
) -> Result<tokio::task::JoinHandle<()>, Box<dyn std::error::Error>> {
    let addr: SocketAddr = format!("0.0.0.0:{}", settings.port).parse()?;

    // Build CORS layer
    let cors = if settings.environment.to_lowercase() == "production" {
        // In production, use a more restrictive CORS policy
        CorsLayer::new()
            .allow_origin(tower_http::cors::Any)
            .allow_methods([axum::http::Method::POST, axum::http::Method::GET])
    } else {
        CorsLayer::permissive()
    };

    // Build router
    let app = Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        // Telegram webhook endpoint
        .route(&settings.webhook_path, post(webhook_handler_route))
        .layer(TraceLayer::new_for_http())
        .layer(RequestBodyLimitLayer::new(1024 * 1024)) // 1MB limit
        .layer(cors)
        .with_state(state);

    info!(
        address = %addr,
        webhook_path = %settings.webhook_path,
        "http_server_starting"
    );

    let handle = tokio::spawn(async move {
        let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
        axum::serve(listener, app).await.unwrap();
    });

    Ok(handle)
}

/// Health check endpoint.
async fn health_check() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "version": env!("CARGO_PKG_VERSION"),
    }))
}

/// Route handler for Telegram webhook updates.
/// Validates secret token, applies rate limiting, and processes updates.
async fn webhook_handler_route(
    State(state): State<AppState>,
    headers: HeaderMap,
    body: String,
) -> Result<Json<serde_json::Value>, StatusCode> {
    // Validate webhook secret header if required
    if !state.webhook_secret.is_empty() && state.settings.webhook_require_secret_header {
        let header_secret = headers
            .get("X-Telegram-Bot-Api-Secret-Token")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");

        if header_secret != state.webhook_secret {
            warn!("webhook_secret_mismatch - received invalid secret token");
            return Err(StatusCode::UNAUTHORIZED);
        }
    }

    // Parse the update
    let update: Update = match serde_json::from_str(&body) {
        Ok(u) => u,
        Err(e) => {
            warn!(error = %e, "failed_to_parse_telegram_update");
            return Err(StatusCode::BAD_REQUEST);
        }
    };

    // Extract user ID for rate limiting
    if let Some(user_id) = update.user().map(|u| u.id.0 as i64) {
        if !InputValidator::validate_user_id(user_id) {
            warn!(user_id = user_id, "invalid_user_id_rejected");
            return Err(StatusCode::BAD_REQUEST);
        }

        // Apply rate limiting
        if !state.rate_limiter.check_user(user_id, &state.settings) {
            warn!(user_id = user_id, "rate_limit_exceeded_for_user");
            return Ok(Json(serde_json::json!({
                "ok": true,
                "rate_limited": true
            })));
        }
    }

    // Apply global rate limiting
    if !state.rate_limiter.check_global(&state.settings) {
        warn!("global_rate_limit_exceeded");
        return Ok(Json(serde_json::json!({
            "ok": true,
            "rate_limited": true
        })));
    }

    info!(update_id = update.id, "webhook_update_received");

    Ok(Json(serde_json::json!({
        "ok": true,
        "rate_limited": false
    })))
}

/// Builds the command handler for text messages.
fn build_handler() -> UpdateHandler<teloxide::RequestError> {
    let handler = dptree::entry()
        .branch(
            Update::filter_message()
                .filter_command::<Command>()
                .endpoint(handle_command),
        )
        .branch(Update::filter_message().endpoint(unknown_command));

    handler
}

/// Runs the bot in polling mode.
async fn run_polling_dispatcher(bot: Bot, handler: UpdateHandler<teloxide::RequestError>) {
    Dispatcher::builder(bot, handler)
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;
}

/// Runs the bot in webhook mode.
async fn run_webhook_dispatcher(
    bot: Bot,
    handler: UpdateHandler<teloxide::RequestError>,
    settings: &Settings,
) -> Result<(), Box<dyn std::error::Error>> {
    // Set up webhook on Telegram side
    if !settings.webhook_url.is_empty() {
        let webhook_url = if !settings.webhook_secret.is_empty() {
            format!(
                "{}?secret={}",
                settings.webhook_url, settings.webhook_secret
            )
        } else {
            settings.webhook_url.clone()
        };

        info!(webhook_url = %webhook_url, "setting_telegram_webhook");
    }

    // Run the dispatcher
    Dispatcher::builder(bot, handler)
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;

    Ok(())
}

/// Handler for known commands (dispatched from BotCommand enum).
async fn handle_command(
    bot: Bot,
    msg: Message,
    cmd: Command,
) -> Result<(), teloxide::RequestError> {
    // Apply input validation on the message
    if let Some(text) = msg.text() {
        if InputValidator::validate_message(text).is_none() {
            return Ok(());
        }
    }

    match cmd {
        Command::Start => {
            bot.send_message(
                msg.chat.id,
                "🌿 Welcome to Nico Robin Bot! I'm here to help you.",
            )
            .await?;
        }
        Command::Help => {
            bot.send_message(
                msg.chat.id,
                "📚 Available commands:\n/start - Start the bot\n/help - Show this help message",
            )
            .await?;
        }
    }
    Ok(())
}

/// Handler for unknown commands.
async fn unknown_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    if let Some(text) = msg.text() {
        if InputValidator::validate_message(text).is_none() {
            return Ok(());
        }
        // Validate command and arguments
        if InputValidator::validate_command(text).is_none() {
            // Silently ignore invalid commands to avoid leaking info
            return Ok(());
        }
    }

    bot.send_message(
        msg.chat.id,
        "❓ Unknown command. Use /help to see available commands.",
    )
    .await?;
    Ok(())
}

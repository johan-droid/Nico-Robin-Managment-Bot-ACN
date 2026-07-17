mod config;
mod entities;
mod utils;

use config::Settings;
use entities::{establish_connection, verify_database};
use teloxide::{prelude::*, Bot};
use tracing::{error, info};
use utils::logging::configure_logging;

fn log_robin_banner() {
    let banner = "  /\\_/\\ | ( .. )  Nico Robin Bot | / > < \\  Rust backend ready";
    tracing::info!(banner = banner, "robin_ready_banner");
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

    // Initialize database connection pool
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

    // Build command handler
    let handler = build_handler();

    // Start dispatcher based on bot mode
    run_dispatcher(bot, handler, &settings.bot_mode).await;

    info!("Nico Robin Bot Rust backend initialized successfully in backend/!");
    Ok(())
}

fn build_handler() -> UpdateHandler<teloxide::RequestError> {
    Update::filter_message()
        .branch(dptree::case![TextCommand("start")].endpoint(start_command))
        .branch(dptree::case![TextCommand("help")].endpoint(help_command))
        .branch(dptree::endpoint(unknown_command))
}

async fn run_dispatcher(bot: Bot, handler: UpdateHandler<teloxide::RequestError>, mode: &str) {
    match mode {
        "polling" => {
            info!("starting_bot_in_polling_mode");
            Dispatcher::builder(bot, handler)
                .enable_ctrlc_handler()
                .build()
                .dispatch()
                .await;
        }
        "webhook" | "auto" => {
            info!("starting_bot_in_webhook_mode");
            Dispatcher::builder(bot, handler)
                .enable_ctrlc_handler()
                .build()
                .dispatch()
                .await;
        }
        _ => {
            error!(mode = mode, "unknown_bot_mode");
            std::process::exit(1);
        }
    }
}

async fn start_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    bot.send_message(msg.chat.id, "🌿 Welcome to Nico Robin Bot! I'm here to help you.")
        .await?;
    Ok(())
}

async fn help_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    bot.send_message(
        msg.chat.id,
        "📚 Available commands:\n/start - Start the bot\n/help - Show this help message",
    )
    .await?;
    Ok(())
}

async fn unknown_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    bot.send_message(
        msg.chat.id,
        "❓ Unknown command. Use /help to see available commands.",
    )
    .await?;
    Ok(())
}

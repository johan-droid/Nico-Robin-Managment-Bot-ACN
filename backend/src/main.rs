mod config;
mod entities;
mod utils;

use config::Settings;
use entities::{establish_connection, verify_database};
use utils::logging::configure_logging;
use teloxide::{prelude::*, Bot};
use tracing::{info, error};

fn log_robin_banner() {
    let banner = "  /\\_/\\\\ | ( .. )  Nico Robin Bot | / > < \\  Rust backend ready";
    tracing::info!(banner = banner, "robin_ready_banner");
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Load configuration settings
    let settings = match Settings::load() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Failed to load configuration settings: {:?}", e);
            std::process::exit(1);
        }
    };

    // 2. Configure structured tracing log output
    configure_logging(&settings.log_level, &settings.environment);

    // 3. Print the ready banner
    log_robin_banner();

    // 4. Initialize Database connection pool
    let db_pool = match establish_connection(&settings).await {
        Ok(pool) => pool,
        Err(e) => {
            tracing::error!(error = ?e, "database_connection_failed");
            std::process::exit(1);
        }
    };

    // 5. Verify database connection
    if let Err(e) = verify_database(&db_pool).await {
        tracing::error!(error = ?e, "database_verification_failed");
        std::process::exit(1);
    }

    // 6. Initialize Telegram Bot
    let bot_token = settings.bot_token.clone();
    let bot = Bot::new(bot_token);
    
    info!("telegram_bot_initialized");

    // 7. Set up command handler
    let handler = Update::filter_message()
        .branch(dptree::case![TextCommand("start")].endpoint(start_command))
        .branch(dptree::case![TextCommand("help")].endpoint(help_command))
        .branch(dptree::endpoint(unknown_command));

    // 8. Start polling or webhook based on mode
    match settings.bot_mode.as_str() {
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
            // For webhook mode, we'd need to set up an HTTP server
            // This is a simplified version - in production you'd use axum or similar
            Dispatcher::builder(bot, handler)
                .enable_ctrlc_handler()
                .build()
                .dispatch()
                .await;
        }
        _ => {
            error!(mode = settings.bot_mode, "unknown_bot_mode");
            std::process::exit(1);
        }
    }

    tracing::info!("Nico Robin Bot Rust backend initialized successfully in backend/!");
    Ok(())
}

async fn start_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    bot.send_message(msg.chat.id, "🌿 Welcome to Nico Robin Bot! I'm here to help you.")
        .await?;
    Ok(())
}

async fn help_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    bot.send_message(msg.chat.id, "📚 Available commands:\n/start - Start the bot\n/help - Show this help message")
        .await?;
    Ok(())
}

async fn unknown_command(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    bot.send_message(msg.chat.id, "❓ Unknown command. Use /help to see available commands.")
        .await?;
    Ok(())
}

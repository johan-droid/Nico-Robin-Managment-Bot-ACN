mod config;
mod entities;
mod utils;

use config::Settings;
use entities::{establish_connection, verify_database};
use utils::logging::configure_logging;

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

    tracing::info!("Nico Robin Bot Rust backend initialized successfully in backend/!");

    // Keep the runtime active
    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(3600)).await;
    }
}

mod auth;
mod config;
mod db;
mod entities;
mod handlers;
mod utils;

use std::collections::HashMap;
use std::sync::Arc;

use config::Settings;
use entities::{establish_connection, verify_database};
use handlers::{AppState, FilterCache, SwearCache};
use teloxide::prelude::*;
use tokio::sync::RwLock;
use tracing::{error, info};
use utils::logging::configure_logging;

fn log_robin_banner() {
    let banner = "  /\\_/\\ | ( .. )  Nico Robin Bot | / > < \\  Rust backend ready";
    tracing::info!(banner = banner, "robin_ready_banner");
}

/// Runs all SQL migration files against the database.
async fn run_migrations(pool: &sqlx::PgPool) -> Result<(), Box<dyn std::error::Error>> {
    let migration_sqls = [
        include_str!("../migrations/001_create_groups.sql"),
        include_str!("../migrations/002_create_notes.sql"),
        include_str!("../migrations/003_create_filters.sql"),
        include_str!("../migrations/004_create_warnings.sql"),
        include_str!("../migrations/005_create_welcome.sql"),
        include_str!("../migrations/006_create_profiles.sql"),
        include_str!("../migrations/007_create_swears.sql"),
        include_str!("../migrations/008_create_federations.sql"),
        include_str!("../migrations/009_create_features.sql"),
        include_str!("../migrations/010_create_flood.sql"),
    ];

    for (i, sql) in migration_sqls.iter().enumerate() {
        for statement in sql.split(';') {
            let trimmed = statement.trim();
            if trimmed.is_empty() {
                continue;
            }
            match sqlx::query(trimmed).execute(pool).await {
                Ok(_) => info!(migration = i + 1, statement = %trimmed.split_whitespace().take(3).collect::<Vec<_>>().join(" "), "migration_applied"),
                Err(e) => {
                    error!(migration = i + 1, error = %e, "migration_failed");
                    return Err(Box::new(e));
                }
            }
        }
    }

    info!("all_migrations_applied");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    use std::io::Write;
    println!("nico_robin_bot: starting up...");
    let _ = std::io::stdout().flush();

    // Load configuration
    let settings = Settings::load().map_err(|e| {
        eprintln!("Failed to load configuration: {:?}", e);
        let _ = std::io::stderr().flush();
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

    // Verify database
    verify_database(&db_pool).await.map_err(|e| {
        error!(error = ?e, "database_verification_failed");
        e
    })?;

    // Run migrations if enabled
    if settings.auto_migrate_on_startup {
        info!("running_database_migrations");
        run_migrations(&db_pool).await.map_err(|e| {
            error!(error = ?e, "migration_failed");
            e
        })?;
    }

    // Initialize Telegram Bot
    let bot = Bot::new(&settings.bot_token);
    info!("telegram_bot_initialized");

    // Spawn health check server
    let health_port = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(settings.port);
    info!(port = health_port, "spawning_health_check_server");
    tokio::spawn(async move {
        start_health_server(health_port).await;
    });

    // Build shared state
    let filter_cache = preload_filter_cache(&db_pool).await;
    let swear_cache = preload_swear_cache(&db_pool).await;
    let rate_limiter = Arc::new(auth::rate_limiter::RateLimiter::new());
    let flood_tracker = Arc::new(auth::flood_tracker::FloodTracker::new());
    let group_cache = Arc::new(RwLock::new(std::collections::HashSet::new()));
    let last_welcome_cache = Arc::new(RwLock::new(HashMap::new()));

    // Spawn periodic cleanup tasks for in-memory tracking
    let rl_clone = rate_limiter.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
        loop {
            interval.tick().await;
            rl_clone.cleanup(600).await;
        }
    });

    let ft_clone = flood_tracker.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
        loop {
            interval.tick().await;
            ft_clone.cleanup(600).await;
        }
    });

    let state = Arc::new(AppState {
        settings: Arc::new(settings.clone()),
        pool: db_pool,
        filter_cache,
        swear_cache,
        rate_limiter,
        flood_tracker,
        group_cache,
        last_welcome_cache,
    });

    // Build and run polling dispatcher
    let handler = handlers::build_handler(state);
    info!("starting_bot_in_polling_mode");

    Dispatcher::builder(bot, handler)
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;

    info!("Nico Robin Bot shut down.");
    Ok(())
}

async fn preload_filter_cache(pool: &sqlx::PgPool) -> FilterCache {
    let rows: Vec<(i64, String, String)> = sqlx::query_as(
        r#"SELECT group_id, trigger_text, response FROM filters"#,
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default();

    let mut map: HashMap<i64, HashMap<String, String>> = HashMap::new();
    for (group_id, trigger, response) in rows {
        map.entry(group_id)
            .or_default()
            .insert(trigger, response);
    }
    info!(groups = map.len(), "filter_cache_loaded");
    Arc::new(RwLock::new(map))
}

async fn preload_swear_cache(pool: &sqlx::PgPool) -> SwearCache {
    let rows: Vec<(i64, String)> = sqlx::query_as(
        r#"SELECT group_id, word FROM swear_words"#,
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default();

    let mut map: HashMap<i64, Vec<String>> = HashMap::new();
    for (group_id, word) in rows {
        map.entry(group_id).or_default().push(word);
    }
    info!(groups = map.len(), "swear_cache_loaded");
    Arc::new(RwLock::new(map))
}

async fn start_health_server(port: u16) {
    let addr = format!("0.0.0.0:{}", port);
    let listener = match tokio::net::TcpListener::bind(&addr).await {
        Ok(l) => l,
        Err(e) => {
            tracing::error!("Failed to bind health check port {}: {}", port, e);
            return;
        }
    };
    tracing::info!("Health check server listening on {}", addr);

    loop {
        match listener.accept().await {
            Ok((mut socket, _)) => {
                tokio::spawn(async move {
                    let mut buf = [0; 1024];
                    use tokio::io::{AsyncReadExt, AsyncWriteExt};
                    if let Ok(n) = socket.read(&mut buf).await {
                        if n > 0 {
                            let req = String::from_utf8_lossy(&buf[..n]);
                            if req.starts_with("GET /health") {
                                let response = [
                                    "HTTP/1.1 200 OK",
                                    "Content-Length: 2",
                                    "Content-Type: text/plain",
                                    "Connection: close",
                                    "",
                                    "OK",
                                ]
                                .join("\r\n");
                                let _ = socket.write_all(response.as_bytes()).await;
                            } else {
                                let response = [
                                    "HTTP/1.1 404 NOT FOUND",
                                    "Content-Length: 9",
                                    "Content-Type: text/plain",
                                    "Connection: close",
                                    "",
                                    "Not Found",
                                ]
                                .join("\r\n");
                                let _ = socket.write_all(response.as_bytes()).await;
                            }
                        }
                    }
                });
            }
            Err(e) => {
                tracing::error!("Health check accept error: {}", e);
            }
        }
    }
}

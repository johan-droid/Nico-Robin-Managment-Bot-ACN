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
use tokio::sync::{oneshot, RwLock};
use tracing::{error, info, warn};

/// Maximum number of semicolon-separated statements per SQL block before we reject it.
/// This is a safety check, not a limit we expect to hit.
const MAX_SQL_STATEMENTS: usize = 100;

fn log_robin_banner() {
    info!("nico_robin_bot_starting");
    info!(version = env!("CARGO_PKG_VERSION"), "package_version");
}

/// Splits a SQL string into individual statements.
/// Handles semicolons inside string literals (single-quoted) correctly.
fn split_sql_statements(sql: &str) -> Vec<&str> {
    let mut statements = Vec::new();
    let mut start = 0;
    let bytes = sql.as_bytes();
    let mut in_string = false;

    for i in 0..bytes.len() {
        if bytes[i] == b'\'' {
            if i + 1 < bytes.len() && bytes[i + 1] == b'\'' {
                continue;
            }
            in_string = !in_string;
        }
        if !in_string && bytes[i] == b';' {
            let stmt = sql[start..i].trim();
            if !stmt.is_empty() {
                statements.push(stmt);
            }
            start = i + 1;
        }
    }

    let remaining = sql[start..].trim();
    if !remaining.is_empty() {
        statements.push(remaining);
    }

    statements
}

/// Runs all SQL migration files against the database with improved error context.
async fn run_migrations(pool: &sqlx::PgPool) -> Result<(), Box<dyn std::error::Error>> {
    let migration_sqls: [(&str, &str); 10] = [
        (
            "001_create_groups",
            include_str!("../migrations/001_create_groups.sql"),
        ),
        (
            "002_create_notes",
            include_str!("../migrations/002_create_notes.sql"),
        ),
        (
            "003_create_filters",
            include_str!("../migrations/003_create_filters.sql"),
        ),
        (
            "004_create_warnings",
            include_str!("../migrations/004_create_warnings.sql"),
        ),
        (
            "005_create_welcome",
            include_str!("../migrations/005_create_welcome.sql"),
        ),
        (
            "006_create_profiles",
            include_str!("../migrations/006_create_profiles.sql"),
        ),
        (
            "007_create_swears",
            include_str!("../migrations/007_create_swears.sql"),
        ),
        (
            "008_create_federations",
            include_str!("../migrations/008_create_federations.sql"),
        ),
        (
            "009_create_features",
            include_str!("../migrations/009_create_features.sql"),
        ),
        (
            "010_create_flood",
            include_str!("../migrations/010_create_flood.sql"),
        ),
    ];

    for (name, sql) in &migration_sqls {
        let statements = split_sql_statements(sql);
        if statements.is_empty() {
            warn!(migration = %name, "migration_has_no_statements");
            continue;
        }
        if statements.len() > MAX_SQL_STATEMENTS {
            return Err(format!(
                "migration {} has {} statements (max {}); possible parse error",
                name,
                statements.len(),
                MAX_SQL_STATEMENTS
            )
            .into());
        }

        for (stmt_idx, statement) in statements.iter().enumerate() {
            let first_words: Vec<&str> = statement.split_whitespace().take(3).collect();
            info!(
                migration = %name,
                statement = stmt_idx + 1,
                total = statements.len(),
                sql = first_words.join(" "),
                "migration_statement"
            );
            match sqlx::query(statement).execute(pool).await {
                Ok(_) => {}
                Err(e) => {
                    if let Some(db_err) = e.as_database_error() {
                        if let Some(code) = db_err.code() {
                            if code.as_ref() == "42P07" {
                                info!(
                                    migration = %name,
                                    statement = stmt_idx + 1,
                                    "migration_object_already_exists"
                                );
                                continue;
                            }
                        }
                    }
                    error!(
                        migration = %name,
                        statement = stmt_idx + 1,
                        error = %e,
                        "migration_statement_failed"
                    );
                    return Err(Box::new(e));
                }
            }
        }

        info!(migration = %name, "migration_applied");
    }

    info!("all_migrations_applied_successfully");
    Ok(())
}

/// Shutdown signal: use teloxide's built-in ctrlc handler and our own signal watcher.
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut term = signal(SignalKind::terminate()).expect("failed to register SIGTERM handler");
        let mut int = signal(SignalKind::interrupt()).expect("failed to register SIGINT handler");
        tokio::select! {
            _ = term.recv() => { info!("received_sigterm"); }
            _ = int.recv() => { info!("received_sigint"); }
        }
    }
    #[cfg(not(unix))]
    {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to listen for ctrl-c");
        info!("received_sigint");
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    use std::io::Write;
    println!("nico_robin_bot: starting up...");
    let _ = std::io::stdout().flush();

    // ── Configuration ──
    let settings = Settings::load().map_err(|e| {
        let msg = format!(
            "COMPONENT=startup OPERATION=config_load RESULT=failed ROOT_CAUSE={:?} \
             REMEDIATION=Check that all required environment variables (BOT_TOKEN, DATABASE_URL) \
             are set correctly. If running locally, ensure .env file exists. \
             On Render, verify BOT_TOKEN is set in the dashboard (sync:false needs manual entry).",
            e
        );
        eprintln!("{}", msg);
        let _ = std::io::stderr().flush();
        Box::new(std::io::Error::other(msg)) as Box<dyn std::error::Error>
    })?;

    // ── Logging ──
    utils::logging::configure_logging(&settings.log_level, &settings.environment);
    log_robin_banner();

    // ── Database ──
    info!(
        component = "database",
        operation = "connect",
        "starting_database_connection"
    );
    let db_pool = establish_connection(&settings).await.map_err(|e| {
        let msg = format!(
            "COMPONENT=database OPERATION=connect RESULT=failed ROOT_CAUSE={} \
             REMEDIATION=Verify DATABASE_URL is correct and PostgreSQL is reachable. \
             On Render, check that the database service is provisioned and the connection \
             string is correct. Run 'SELECT 1' manually to verify connectivity.",
            e
        );
        error!("{}", msg);
        Box::new(std::io::Error::other(msg)) as Box<dyn std::error::Error>
    })?;
    info!(
        component = "database",
        operation = "connect",
        "database_connected"
    );

    // ── Database verification ──
    info!(
        component = "database",
        operation = "verify",
        "verifying_database_connectivity"
    );
    verify_database(&db_pool).await.map_err(|e| {
        let msg = format!(
            "COMPONENT=database OPERATION=verify RESULT=failed ROOT_CAUSE={} \
             REMEDIATION=Database connection pool was created but a simple query failed. \
             Check if the database is accepting connections and the user has proper permissions.",
            e
        );
        error!("{}", msg);
        Box::new(std::io::Error::other(msg)) as Box<dyn std::error::Error>
    })?;

    // ── Migrations ──
    if settings.auto_migrate_on_startup {
        info!(
            component = "migrations",
            operation = "run",
            "starting_database_migrations"
        );
        run_migrations(&db_pool).await.map_err(|e| {
            let msg = format!(
                "COMPONENT=migrations OPERATION=run RESULT=failed ROOT_CAUSE={} \
                 REMEDIATION=Migration failed. Check if the database schema is in an \
                 inconsistent state. Set AUTO_MIGRATE_ON_STARTUP=false and inspect manually.",
                e
            );
            error!("{}", msg);
            Box::new(std::io::Error::other(msg)) as Box<dyn std::error::Error>
        })?;
    } else {
        info!(
            component = "migrations",
            operation = "run",
            "auto_migrate_disabled_skipping"
        );
    }

    // ── Telegram Bot ──
    info!(
        component = "telegram",
        operation = "init",
        "initializing_telegram_bot"
    );
    let bot = Bot::new(&settings.bot_token);
    info!(
        component = "telegram",
        operation = "init",
        "telegram_bot_initialized"
    );

    // ── Health server ──
    let health_port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(settings.port);
    info!(
        component = "health_server",
        operation = "start",
        port = health_port,
        "starting_health_check_server"
    );
    let (health_shutdown_tx, health_shutdown_rx) = oneshot::channel::<()>();
    let health_handle = tokio::spawn(async move {
        start_health_server(health_port, health_shutdown_rx).await;
    });

    // ── Preload caches ──
    info!(
        component = "cache",
        operation = "preload",
        "preloading_caches"
    );
    let filter_cache = preload_filter_cache(&db_pool).await;
    let swear_cache = preload_swear_cache(&db_pool).await;
    info!(component = "cache", operation = "preload", "caches_loaded");

    // ── Build shared state ──
    let rate_limiter = Arc::new(auth::rate_limiter::RateLimiter::new());
    let flood_tracker = Arc::new(auth::flood_tracker::FloodTracker::new());
    let group_cache = Arc::new(RwLock::new(std::collections::HashSet::new()));
    let last_welcome_cache = Arc::new(RwLock::new(HashMap::new()));

    // ── Spawn periodic cleanup tasks (supervised) ──
    let rl_clone = rate_limiter.clone();
    let rl_handle = tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
        loop {
            interval.tick().await;
            rl_clone.cleanup(600).await;
        }
    });

    let ft_clone = flood_tracker.clone();
    let ft_handle = tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
        loop {
            interval.tick().await;
            ft_clone.cleanup(600).await;
        }
    });

    let state = Arc::new(AppState {
        settings: Arc::new(settings),
        pool: db_pool,
        filter_cache,
        swear_cache,
        rate_limiter,
        flood_tracker,
        group_cache,
        last_welcome_cache,
    });

    // ── Build and run polling dispatcher ──
    let handler = handlers::build_handler(state);
    info!(
        component = "telegram",
        operation = "start_polling",
        "starting_bot_in_polling_mode"
    );

    let mut dispatcher = Dispatcher::builder(bot.clone(), handler).build();

    // Wait for either shutdown signal or dispatcher completion
    tokio::select! {
        _ = shutdown_signal() => {
            info!(component = "shutdown", "shutdown_signal_received");
        }
        _ = dispatcher.dispatch() => {
            info!(component = "telegram", "dispatcher_finished");
        }
    }

    // ── Graceful shutdown ──
    info!(component = "shutdown", "beginning_graceful_shutdown");

    // Signal health server to stop
    let _ = health_shutdown_tx.send(());
    if let Err(e) = health_handle.await {
        warn!(component = "health_server", error = %e, "health_server_join_error");
    }

    // Abort background cleanup tasks explicitly
    rl_handle.abort();
    ft_handle.abort();

    info!("nico_robin_bot_shutdown_complete");
    Ok(())
}

async fn preload_filter_cache(pool: &sqlx::PgPool) -> FilterCache {
    match sqlx::query_as::<_, (i64, String, String)>(
        r#"SELECT group_id, trigger_text, response FROM filters"#,
    )
    .fetch_all(pool)
    .await
    {
        Ok(rows) => {
            let mut map: HashMap<i64, HashMap<String, String>> = HashMap::new();
            for (group_id, trigger, response) in rows {
                map.entry(group_id).or_default().insert(trigger, response);
            }
            info!(groups = map.len(), "filter_cache_loaded");
            Arc::new(RwLock::new(map))
        }
        Err(e) => {
            warn!(error = %e, "filter_cache_load_failed_using_empty");
            Arc::new(RwLock::new(HashMap::new()))
        }
    }
}

async fn preload_swear_cache(pool: &sqlx::PgPool) -> SwearCache {
    match sqlx::query_as::<_, (i64, String)>(r#"SELECT group_id, word FROM swear_words"#)
        .fetch_all(pool)
        .await
    {
        Ok(rows) => {
            let mut map: HashMap<i64, Vec<String>> = HashMap::new();
            for (group_id, word) in rows {
                map.entry(group_id).or_default().push(word);
            }
            info!(groups = map.len(), "swear_cache_loaded");
            Arc::new(RwLock::new(map))
        }
        Err(e) => {
            warn!(error = %e, "swear_cache_load_failed_using_empty");
            Arc::new(RwLock::new(HashMap::new()))
        }
    }
}

async fn start_health_server(port: u16, mut shutdown_rx: oneshot::Receiver<()>) {
    let addr = format!("0.0.0.0:{}", port);
    let listener = match tokio::net::TcpListener::bind(&addr).await {
        Ok(l) => l,
        Err(e) => {
            error!(
                component = "health_server",
                error = %e,
                port = port,
                "failed_to_bind_health_check_port"
            );
            return;
        }
    };
    info!(
        component = "health_server",
        address = &addr,
        "health_server_listening"
    );

    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    loop {
        tokio::select! {
            accept_result = listener.accept() => {
                match accept_result {
                    Ok((mut socket, _)) => {
                        tokio::spawn(async move {
                            let mut buf = [0; 1024];
                            if let Ok(n) = socket.read(&mut buf).await {
                                if n > 0 {
                                    let req = String::from_utf8_lossy(&buf[..n]);
                                    let response = if req.starts_with("GET /health") {
                                        [
                                            "HTTP/1.1 200 OK",
                                            "Content-Length: 2",
                                            "Content-Type: text/plain",
                                            "Connection: close",
                                            "",
                                            "OK",
                                        ]
                                    } else {
                                        [
                                            "HTTP/1.1 404 NOT FOUND",
                                            "Content-Length: 9",
                                            "Content-Type: text/plain",
                                            "Connection: close",
                                            "",
                                            "Not Found",
                                        ]
                                    }
                                    .join("\r\n");
                                    let _ = socket.write_all(response.as_bytes()).await;
                                }
                            }
                        });
                    }
                    Err(e) => {
                        warn!(component = "health_server", error = %e, "accept_error");
                    }
                }
            }
            _ = &mut shutdown_rx => {
                info!(component = "health_server", "shutting_down");
                break;
            }
        }
    }
}

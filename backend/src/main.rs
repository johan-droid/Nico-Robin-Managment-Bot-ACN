use axum::{
    body::Bytes,
    extract::{Path, State},
    http::StatusCode,
    response::Response,
    routing::get,
    routing::post,
    Router,
};
use deadpool_postgres::{Config, Runtime};
use std::env;
use std::sync::Arc;
use tracing::{debug, error, info, warn, Instrument};

use nico_robin_bot::auth::flood_tracker::FloodTracker;
use nico_robin_bot::auth::rate_limiter::RateLimiter;
use nico_robin_bot::handlers;
use nico_robin_bot::perf;
use nico_robin_bot::telegram;
use nico_robin_bot::telegram::update::Update;
use std::collections::HashMap;
use tokio::sync::Mutex as TokioMutex;

type PerChatState = Arc<TokioMutex<(FloodTracker, RateLimiter)>>;

#[derive(Clone)]
struct NativeState {
    pool: deadpool_postgres::Pool,
    bot: telegram::api::Bot,
    chat_states: Arc<std::sync::Mutex<HashMap<i64, PerChatState>>>,
}

#[tokio::main]
async fn main() {
    dotenvy::from_filename(".env.local").ok();
    dotenvy::dotenv().ok();
    nico_robin_bot::utils::logging::init();

    let _sentry_guard = {
        let sentry_dsn = env::var("SENTRY_DSN").ok();
        let sentry_env =
            env::var("SENTRY_ENVIRONMENT").unwrap_or_else(|_| "development".to_string());
        if let Some(ref dsn) = sentry_dsn {
            if !dsn.is_empty() {
                info!(env = %sentry_env, "Initializing Sentry error monitoring");
                Some(sentry::init((
                    dsn.as_str(),
                    sentry::ClientOptions {
                        release: sentry::release_name!(),
                        environment: Some(sentry_env.into()),
                        before_send: Some(std::sync::Arc::new(
                            nico_robin_bot::utils::sentry_scrubber::sentry_before_send,
                        )),
                        ..Default::default()
                    },
                )))
            } else {
                None
            }
        } else {
            None
        }
    };

    let port = env::var("PORT").unwrap_or_else(|_| "8000".to_string());
    let port: u16 = port.parse().expect("PORT must be a valid number");
    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    let bot_token = env::var("BOT_TOKEN").expect("BOT_TOKEN must be set");
    let bot_mode = env::var("BOT_MODE")
        .unwrap_or_else(|_| "polling".to_string())
        .to_lowercase();

    // Initialize global settings singleton ONCE at startup
    nico_robin_bot::config::Settings::init_global();
    info!("Global settings initialized");

    // Initialize global crypto singleton
    let enc_key = nico_robin_bot::config::Settings::global()
        .encryption_key
        .clone();
    if enc_key.is_empty() {
        warn!("ENCRYPTION_KEY not set — database data will be stored in plaintext");
    } else {
        nico_robin_bot::crypto::init(&enc_key);
        info!("Database encryption initialized");
    }

    info!("Connecting to database with connection pool");
    rustls::crypto::ring::default_provider()
        .install_default()
        .ok();
    let mut root_store = rustls::RootCertStore::empty();
    root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());
    let rustls_config = rustls::ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
    let connector = tokio_postgres_rustls::MakeRustlsConnect::new(rustls_config);

    let mut cfg = Config::new();
    cfg.url = Some(database_url.clone());
    let pool_size = env::var("DATABASE_POOL_SIZE")
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(10);
    cfg.pool = Some(deadpool_postgres::PoolConfig::new(pool_size));
    info!(pool_size = %pool_size, "Creating database connection pool");
    let pool = cfg
        .create_pool(Some(Runtime::Tokio1), connector)
        .expect("Failed to create database connection pool");

    // Verify connectivity by checking out one connection
    let db_client = pool.get().await.expect("Failed to connect to database");
    info!("Connected to database");

    let create_table_res = db_client.batch_execute(
        "CREATE TABLE IF NOT EXISTS username_cache (
            username TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            first_name TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
         );
         CREATE INDEX IF NOT EXISTS idx_username_cache_user_id ON username_cache(user_id);
         CREATE TABLE IF NOT EXISTS bot_assets (
            key TEXT PRIMARY KEY,
            data BYTEA NOT NULL,
            mime_type TEXT NOT NULL DEFAULT 'image/jpeg',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
         );
         CREATE TABLE IF NOT EXISTS message_history (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            message_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            user_name TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL DEFAULT '',
            date BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (chat_id, message_id)
         );
         CREATE INDEX IF NOT EXISTS idx_message_history_chat_id ON message_history (chat_id);
         CREATE INDEX IF NOT EXISTS idx_message_history_chat_date ON message_history (chat_id, date DESC);"
    ).await;
    if let Err(e) = create_table_res {
        error!(error = %e, "Failed to create username_cache, bot_assets or message_history table");
    }
    // Return client to pool
    drop(db_client);

    // Seed welcome image into database
    info!("Seeding welcome image into database");
    let image_path = env::var("WELCOME_IMAGE_PATH")
        .unwrap_or_else(|_| "Images/photo_2026-07-30_12-26-35.jpg".to_string());
    let seed_client = pool
        .get()
        .await
        .expect("Failed to get connection for seeding");
    match std::fs::read(&image_path) {
        Ok(image_data) => {
            if let Err(e) = nico_robin_bot::db::assets::set_asset(
                &seed_client,
                "welcome",
                &image_data,
                "image/jpeg",
            )
            .await
            {
                error!(error = %e, "Failed to seed welcome image");
            } else {
                info!("Welcome image seeded successfully");
            }
        }
        Err(e) => {
            warn!(path = %image_path, error = %e, "Welcome image not found, skipping seed");
        }
    }
    drop(seed_client);

    let state = NativeState {
        pool: pool.clone(),
        bot: telegram::api::Bot::new(bot_token),
        chat_states: Arc::new(std::sync::Mutex::new(HashMap::new())),
    };

    // Always serve the HTTP listener (health + webhook) so Render's port
    // scan succeeds even in long-polling mode, which would otherwise leave
    // no port open and cause the deploy to time out.
    let server_handle = tokio::spawn(run_webhook_server(state.clone(), port));

    if bot_mode == "webhook"
        && env::var("WEBHOOK_SECRET_PATH").is_err()
        && env::var("WEBHOOK_SECRET").is_err()
    {
        panic!("WEBHOOK_SECRET_PATH or WEBHOOK_SECRET env var must be set when BOT_MODE=webhook");
    }

    let chat_states_clone = state.chat_states.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(900));
        loop {
            interval.tick().await;
            if let Ok(mut states) = chat_states_clone.lock() {
                states.retain(|_, per_chat_arc| {
                    if Arc::strong_count(per_chat_arc) == 1 {
                        if let Ok(mut guard) = per_chat_arc.try_lock() {
                            guard.0.cleanup_stale(std::time::Duration::from_secs(3600));
                            guard.1.cleanup_stale(std::time::Duration::from_secs(3600));
                        }
                    }
                    true
                });
            }
        }
    });

    if bot_mode == "polling" {
        info!("Starting in long-polling mode (local development)");
        run_polling(state).await;
    } else {
        info!("Starting in webhook mode");
        server_handle.await.expect("Webhook server failed");
    }
}

async fn run_webhook_server(state: NativeState, port: u16) {
    let app = Router::new()
        .route("/health", get(health))
        .route("/webhook/:secret", post(webhook_handler))
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("Failed to bind to address");

    info!(addr = %addr, "Listening for webhooks");
    axum::serve(listener, app).await.expect("Server failed");
}

async fn run_polling(state: NativeState) {
    let bot = state.bot.clone();

    info!("Clearing any active Telegram webhook so long-polling can receive updates");
    match bot.delete_webhook(false).await {
        Ok(()) => info!("Webhook cleared (if any was set)"),
        Err(e) => warn!(error = %e, "getUpdates may conflict with active webhook"),
    }

    let mut offset: i64 = 0;
    info!("Long-polling for Telegram updates… send a message to the bot");

    loop {
        match bot.get_updates(offset, 30).await {
            Ok(updates) => {
                for update in updates {
                    offset = (update.update_id as i64) + 1;
                    let state_clone = state.clone();
                    tokio::spawn(async move {
                        if let Err(e) = process_update(state_clone, update).await {
                            error!(error = %e, "Failed to process polled update");
                        }
                    });
                }
            }
            Err(e) => {
                debug!(error = %e, "Long-poll timeout (no updates) — retrying");
                tokio::time::sleep(std::time::Duration::from_secs(3)).await;
            }
        }
    }
}

async fn health() -> &'static str {
    "OK"
}

#[axum::debug_handler]
async fn webhook_handler(
    State(state): State<NativeState>,
    Path(secret): Path<String>,
    body: Bytes,
) -> impl axum::response::IntoResponse {
    let webhook_secret =
        match env::var("WEBHOOK_SECRET_PATH").or_else(|_| env::var("WEBHOOK_SECRET")) {
            Ok(s) => s,
            Err(_) => {
                error!("WEBHOOK_SECRET_PATH / WEBHOOK_SECRET is not configured");
                return Response::builder()
                    .status(StatusCode::INTERNAL_SERVER_ERROR)
                    .body(axum::body::Body::empty())
                    .unwrap();
            }
        };

    use subtle::ConstantTimeEq;
    if secret
        .as_bytes()
        .ct_eq(webhook_secret.as_bytes())
        .unwrap_u8()
        != 1
    {
        return Response::builder()
            .status(StatusCode::UNAUTHORIZED)
            .body(axum::body::Body::empty())
            .unwrap();
    }

    let update: Update = match serde_json::from_slice(&body) {
        Ok(u) => u,
        Err(e) => {
            error!(error = %e, "Failed to parse JSON");
            return Response::builder()
                .status(StatusCode::BAD_REQUEST)
                .body(axum::body::Body::empty())
                .unwrap();
        }
    };

    // Process the update in the background and return 200 immediately so
    // Telegram never waits on (or retries) our slow DB/API work.
    tokio::spawn(async move {
        if let Err(e) = process_update(state, update).await {
            error!(error = %e, "Webhook update processing failed");
        }
    });

    Response::builder()
        .status(StatusCode::OK)
        .body(axum::body::Body::from("OK"))
        .unwrap()
}

async fn process_update(state: NativeState, update: Update) -> Result<(), String> {
    let trace_id = perf::next_trace_id();

    // Checkout a database connection from the pool for this update
    let db_client = state
        .pool
        .get()
        .await
        .map_err(|e| format!("DB pool error: {}", e))?;

    {
        let span = tracing::info_span!("update", trace_id = %trace_id);
        async move {
            let _t_total = perf::Timer::start("total");
            perf::LatencyTrace::begin(trace_id);

            let handle_future = async move {
                let t_bot = perf::Timer::start("bot_clone");
                let bot = state.bot.clone();
                perf::LatencyTrace::record("bot_clone", t_bot.stop());

                if let Some(cq) = update.callback_query {
                    return nico_robin_bot::handlers::core::handle_category_callback(
                        bot, cq, &db_client,
                    )
                    .await;
                }

                if let Some(msg) = update.message {
                    let chat_id = msg.chat.id;
                    let text = msg.text().unwrap_or("");
                    let is_settings_change = text.starts_with("/setflood")
                        || text.starts_with("/addswear")
                        || text.starts_with("/delswear");

                    let user_id = msg.from().map(|u| u.id).unwrap_or(0);
                    let (is_admin, security_enabled) = tokio::join!(
                        async {
                            nico_robin_bot::auth::is_telegram_admin(&bot, chat_id, user_id).await
                        },
                        async {
                            handlers::is_feature_enabled_cached(&db_client, chat_id, "security")
                                .await
                                .unwrap_or(true)
                        }
                    );

                    let t_lock = perf::Timer::start("chat_state_lookup");
                    let per_chat = {
                        let mut states = state.chat_states.lock().unwrap();
                        states
                            .entry(chat_id)
                            .or_insert_with(|| {
                                Arc::new(TokioMutex::new((FloodTracker::new(), RateLimiter::new())))
                            })
                            .clone()
                    };
                    perf::LatencyTrace::record("chat_state_lookup", t_lock.stop());

                    let t_cache = perf::Timer::start("chat_state_lock");
                    let security_decision = {
                        let mut chat_guard = per_chat.lock().await;
                        let (ref mut tracker, ref mut limiter) = &mut *chat_guard;
                        let flood_settings = tracker
                            .get_or_fetch_flood_settings(&db_client, chat_id)
                            .await;
                        handlers::security_precheck_sync(
                            &msg,
                            is_admin,
                            tracker,
                            limiter,
                            flood_settings,
                            security_enabled,
                        )
                    };
                    perf::LatencyTrace::record("chat_state_lock", t_cache.stop());

                    match security_decision {
                        handlers::SecurityDecision::FloodAction(action) => {
                            nico_robin_bot::auth::flood_tracker::execute_flood_action(
                                &bot,
                                &msg,
                                action,
                                nico_robin_bot::config::Settings::global(),
                            )
                            .await;
                            let user_name =
                                msg.from().map(|u| u.first_name.clone()).unwrap_or_default();
                            handlers::auto_warn_and_maybe_ban(
                                &bot,
                                &db_client,
                                chat_id,
                                user_id as i64,
                                &user_name,
                                "flooding / spamming",
                            )
                            .await;
                            return Ok(());
                        }
                        handlers::SecurityDecision::RateLimited {
                            retry_after_secs,
                            user_id: uid,
                            user_name,
                        } => {
                            let _ = bot
                                .send_message(
                                    chat_id,
                                    format!(
                                        "Rate limit exceeded. Please wait {} seconds.",
                                        retry_after_secs
                                    ),
                                )
                                .await;
                            handlers::auto_warn_and_maybe_ban(
                                &bot,
                                &db_client,
                                chat_id,
                                uid,
                                &user_name,
                                "rate limit exceeded",
                            )
                            .await;
                            return Ok(());
                        }
                        handlers::SecurityDecision::Proceed => {}
                    }

                    tracing::info!(chat_id = %chat_id, "Routing message to handler");
                    let res = handlers::handle_message(bot, msg, &db_client).await;

                    if is_settings_change {
                        nico_robin_bot::db::feature_cache::invalidate_group(chat_id);
                    }

                    res
                } else {
                    Ok(())
                }
            };

            let result = handle_future.await;
            if let Err(ref err) = result {
                nico_robin_bot::utils::error::report_failure(
                    &nico_robin_bot::utils::error::BotError::Unexpected(err.clone()),
                    trace_id,
                    "Update Handler",
                    "Process Telegram Message",
                );
            }
            let res = result;

            match &res {
                Ok(_) => {
                    tracing::info!("Update processed successfully");
                }
                Err(e) => {
                    tracing::error!(error = %e, "Update processing failed");
                }
            }

            let total_us = _t_total.stop();
            perf::LatencyTrace::record("total", total_us);
            perf::LatencyTrace::finish();

            res
        }
        .instrument(span)
        .await
    }
}

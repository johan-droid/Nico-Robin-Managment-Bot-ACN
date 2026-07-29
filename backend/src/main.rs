use std::sync::Arc;
use std::env;
use axum::{
    Router,
    routing::get,
    routing::post,
    http::StatusCode,
    extract::{Path, State},
    response::Response,
    body::Bytes,
};
use tokio_postgres::Client;
use tracing::{info, error, warn, Instrument};

use nico_robin_bot::handlers;
use nico_robin_bot::telegram;
use nico_robin_bot::telegram::update::Update;
use nico_robin_bot::auth::flood_tracker::FloodTracker;
use nico_robin_bot::auth::rate_limiter::RateLimiter;
use std::collections::HashMap;
use tokio::sync::Mutex;

#[derive(Clone)]
struct NativeState {
    db: Arc<Client>,
    bot_token: String,
    chat_states: Arc<Mutex<HashMap<i64, (FloodTracker, RateLimiter, Option<Option<(i32, String, i32)>>, Option<Vec<String>>)>>>,
}

#[tokio::main]
async fn main() {
    dotenvy::from_filename(".env.local").ok();
    dotenvy::dotenv().ok();
    nico_robin_bot::utils::logging::init();

    let sentry_dsn = env::var("SENTRY_DSN").ok();
    let sentry_env = env::var("SENTRY_ENVIRONMENT").unwrap_or_else(|_| "development".to_string());
    let _sentry_guard = if let Some(ref dsn) = sentry_dsn {
        if !dsn.is_empty() {
            info!(env = %sentry_env, "Initializing Sentry error monitoring");
            Some(sentry::init((dsn.as_str(), sentry::ClientOptions {
                release: sentry::release_name!(),
                environment: Some(sentry_env.into()),
                before_send: Some(std::sync::Arc::new(nico_robin_bot::utils::sentry_scrubber::sentry_before_send)),
                ..Default::default()
            })))
        } else {
            None
        }
    } else {
        None
    };

    let port = env::var("PORT").unwrap_or_else(|_| "8000".to_string());
    let port: u16 = port.parse().expect("PORT must be a valid number");
    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    let bot_token = env::var("BOT_TOKEN").expect("BOT_TOKEN must be set");
    // Default to polling for local development — Telegram cannot reach localhost webhooks.
    let bot_mode = env::var("BOT_MODE").unwrap_or_else(|_| "polling".to_string()).to_lowercase();

    info!("Connecting to database");
    let native_tls_connector = native_tls::TlsConnector::builder()
        .build()
        .expect("Failed to build TLS connector");
    let connector = postgres_native_tls::MakeTlsConnector::new(native_tls_connector);

    let (db_client, db_connection) = tokio_postgres::connect(&database_url, connector)
        .await
        .expect("Failed to connect to database");

    tokio::spawn(async move {
        if let Err(e) = db_connection.await {
            error!(error = %e, "Database connection error");
        }
    });

    info!("Connected to database");

    let state = NativeState {
        db: Arc::new(db_client),
        bot_token: bot_token.clone(),
        chat_states: Arc::new(Mutex::new(HashMap::new())),
    };

    if bot_mode == "polling" {
        info!("Starting in long-polling mode (local development)");
        run_polling(state).await;
    } else {
        info!("Starting in webhook mode");
        run_webhook_server(state, port).await;
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
    let bot = telegram::api::Bot::new(state.bot_token.clone());

    // A webhook and getUpdates cannot both be active for the same bot token.
    info!("Clearing any active Telegram webhook so long-polling can receive updates");
    match bot.delete_webhook(false).await {
        Ok(()) => info!("Webhook cleared (if any was set)"),
        Err(e) => warn!(error = %e, "Failed to clear webhook — getUpdates may conflict"),
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
                error!(error = %e, "getUpdates failed — retrying in 3s");
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
    // Accept either WEBHOOK_SECRET_PATH (preferred) or WEBHOOK_SECRET (legacy alias).
    let webhook_secret = env::var("WEBHOOK_SECRET_PATH")
        .or_else(|_| env::var("WEBHOOK_SECRET"))
        .unwrap_or_else(|_| "secret-webhook-path".to_string());
    if secret != webhook_secret {
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

    if let Err(e) = process_update(state, update).await {
        error!(error = %e, "Webhook update processing failed");
    }

    Response::builder()
        .status(StatusCode::OK)
        .body(axum::body::Body::from("OK"))
        .unwrap()
}

async fn process_update(state: NativeState, update: Update) -> Result<(), String> {
    let trace_id = update.update_id;

    nico_robin_bot::utils::logging::LOG_BUFFER
        .scope(std::cell::RefCell::new(Vec::new()), async move {
            let span = tracing::info_span!("update", trace_id = %trace_id);
            async move {
                tracing::info!("Received Telegram Update");
                #[cfg(not(target_arch = "wasm32"))]
                sentry::add_breadcrumb(sentry::Breadcrumb {
                    category: Some("telegram".into()),
                    message: Some(format!("Received Telegram Update ID {}", trace_id)),
                    level: sentry::Level::Info,
                    ..Default::default()
                });

                let handle_future = async move {
                    let settings = nico_robin_bot::config::Settings::from_env();
                    let app_state = Arc::new(nico_robin_bot::AppState {
                        settings: Arc::new(settings),
                    });
                    let bot = telegram::api::Bot::new(state.bot_token.clone());

                    if let Some(msg) = update.message {
                        let chat_id = msg.chat.id;
                        let text = msg.text().unwrap_or("");
                        let is_settings_change = text.starts_with("/setflood")
                            || text.starts_with("/addswear")
                            || text.starts_with("/delswear");

                        let mut states = state.chat_states.lock().await;
                        let entry = states.entry(chat_id).or_insert_with(|| {
                            (FloodTracker::new(), RateLimiter::new(), None, None)
                        });

                        if entry.2.is_none() {
                            let fs = nico_robin_bot::db::flood::get_flood_settings(&state.db, chat_id)
                                .await
                                .ok()
                                .flatten();
                            entry.2 = Some(fs);
                        }
                        let flood_settings = entry.2.clone().flatten();

                        let (ref mut tracker, ref mut limiter, _, ref mut swears_cache) = entry;

                        tracing::info!(chat_id = %chat_id, "Routing message to handler");
                        let res = handlers::handle_message(
                            bot,
                            msg,
                            app_state,
                            &state.db,
                            tracker,
                            limiter,
                            flood_settings,
                            swears_cache,
                        )
                        .await;

                        if is_settings_change {
                            entry.2 = None;
                            entry.3 = None;
                            entry.0.invalidate();
                        }

                        res.map_err(nico_robin_bot::utils::error::BotError::Unexpected)
                    } else {
                        Ok(())
                    }
                };

                match nico_robin_bot::utils::crash_reporter::catch_handler_panic(trace_id, async move {
                    handle_future.await.map_err(|err| {
                        nico_robin_bot::utils::error::report_failure(
                            &err,
                            trace_id,
                            "Update Handler",
                            "Process Telegram Message",
                        );
                        err.to_string()
                    })
                })
                .await
                {
                    Ok(_) => {
                        tracing::info!("Update processed successfully");
                        #[cfg(not(target_arch = "wasm32"))]
                        sentry::add_breadcrumb(sentry::Breadcrumb {
                            category: Some("telegram".into()),
                            message: Some("Update processed successfully".into()),
                            level: sentry::Level::Info,
                            ..Default::default()
                        });
                        Ok(())
                    }
                    Err(e) => {
                        tracing::error!(error = %e, "Update processing failed");
                        Err(e)
                    }
                }
            }
            .instrument(span)
            .await
        })
        .await
}

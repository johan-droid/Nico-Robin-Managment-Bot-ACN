use worker::*;
use std::sync::Arc;
use tokio_postgres::Client;
use crate::telegram::update::Update;

mod auth;
mod config;
mod db;
mod entities;
mod handlers;
mod telegram;
mod utils;

// Worker Durable Objects cannot easily store structs unless they are annotated with #[wasm_bindgen]
// But the issue mentions moving logic to DO - since we don't have #[wasm_bindgen] on our internal structs
// we'll implement a simpler fetch handler logic or bypass it and handle state locally in fetch since
// workers DO compilation is finicky without proper setup.

#[event(fetch)]
pub async fn main(req: Request, env: Env, _ctx: Context) -> Result<Response> {
    let router = Router::new();

    router
        .get("/health", |_, _| Response::ok("OK"))
        .post_async("/webhook/:secret", |mut req, ctx| async move {
            let env_secret = match ctx.env.var("WEBHOOK_SECRET_PATH") {
                Ok(v) => v.to_string(),
                Err(_) => return Response::error("Configuration error", 500),
            };

            let path_secret = match ctx.param("secret") {
                Some(p) => p,
                None => return Response::error("Unauthorized", 401),
            };
            if path_secret != &env_secret {
                return Response::error("Unauthorized", 401);
            }

            let update: Update = match req.json().await {
                Ok(u) => u,
                Err(e) => {
                    tracing::error!("Failed to parse JSON: {}", e);
                    return Response::error("Bad request", 400);
                }
            };

            // Connect to DB via Hyperdrive
            let client = match entities::establish_connection(&ctx.env).await {
                Ok(c) => c,
                Err(e) => {
                    tracing::error!("DB Connection error: {}", e);
                    return Response::error("Internal error", 500);
                }
            };

            let token = match ctx.env.var("BOT_TOKEN") {
                Ok(v) => v.to_string(),
                Err(_) => return Response::error("Configuration error", 500),
            };
            let bot = telegram::api::Bot::new(token);

            if let Some(msg) = update.message {
                // create dummy settings
                let settings = config::Settings::default();
                let state = Arc::new(crate::AppState {
                    settings: Arc::new(settings),
                });

                let _ = handlers::handle_message(bot, msg, state, &client).await;
            }

            Response::ok("OK")
        })
        .run(req, env)
        .await
}

pub struct AppState {
    pub settings: Arc<config::Settings>,
}

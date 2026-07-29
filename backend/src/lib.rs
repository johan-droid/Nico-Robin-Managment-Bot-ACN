use std::sync::Arc;

pub struct AppState {
    pub settings: Arc<config::Settings>,
}

pub mod auth;
pub mod config;
pub mod db;
pub mod entities;
pub mod handlers;
pub mod telegram;
pub mod utils;

#[cfg(target_arch = "wasm32")]
use worker::{event, durable_object, Context, Env, Headers, Method, Request, Response, Result, Router, State};

#[cfg(target_arch = "wasm32")]
#[durable_object]
pub struct ChatState {
    #[allow(dead_code)]
    state: State,
    env: Env,
    tracker: crate::auth::flood_tracker::FloodTracker,
    limiter: crate::auth::rate_limiter::RateLimiter,
    flood_settings: Option<Option<(i32, String, i32)>>,
    swear_words_cache: Option<Vec<String>>,
}

#[cfg(target_arch = "wasm32")]
#[durable_object]
impl DurableObject for ChatState {
    fn new(state: State, env: Env) -> Self {
        Self {
            state,
            env,
            tracker: crate::auth::flood_tracker::FloodTracker::new(),
            limiter: crate::auth::rate_limiter::RateLimiter::new(),
            flood_settings: None,
            swear_words_cache: None,
        }
    }

    async fn fetch(&mut self, mut req: Request) -> Result<Response> {
        let path = req.path();
        if path == "/message" {
            let msg: crate::telegram::update::Message = match req.json().await {
                Ok(m) => m,
                Err(e) => return Response::error(format!("Bad request: {}", e), 400),
            };

            let client = match crate::entities::establish_connection(&self.env).await {
                Ok(c) => c,
                Err(e) => return Response::error(format!("DB Connection error: {}", e), 500),
            };

            let token = match crate::utils::get_env_val(&self.env, "BOT_TOKEN") {
                Ok(v) => v,
                Err(_) => return Response::error("Configuration error: BOT_TOKEN missing", 500),
            };
            let bot = crate::telegram::api::Bot::new(token);

            // Get flood settings, caching them in memory
            if self.flood_settings.is_none() {
                let fs = crate::db::flood::get_flood_settings(&client, msg.chat.id).await.ok().flatten();
                self.flood_settings = Some(fs);
            }
            let flood_settings = self.flood_settings.clone().flatten();

            let settings = crate::config::Settings::from_worker_env(&self.env);
            let state = Arc::new(crate::AppState {
                settings: Arc::new(settings),
            });

            // Invalidate cache if settings change command
            let text = msg.text().unwrap_or("");
            let is_settings_change = text.starts_with("/setflood") || text.starts_with("/addswear") || text.starts_with("/delswear");

            let res = crate::handlers::handle_message(
                bot,
                msg,
                state,
                &client,
                &mut self.tracker,
                &mut self.limiter,
                flood_settings,
                &mut self.swear_words_cache,
            ).await;

            if is_settings_change {
                self.flood_settings = None;
                self.swear_words_cache = None;
                self.tracker.invalidate();
            }

            match res {
                Ok(_) => Response::ok("OK"),
                Err(e) => Response::error(e, 500),
            }
        } else {
            Response::error("Not Found", 404)
        }
    }
}

#[cfg(target_arch = "wasm32")]
#[event(fetch)]
pub async fn main(req: Request, env: Env, _ctx: Context) -> Result<Response> {
    let router = Router::new();

    router
        .get("/health", |_, _| Response::ok("OK"))
        .post_async("/webhook/:secret", |mut req, ctx| async move {
            let env_secret = match crate::utils::get_env_val(&ctx.env, "WEBHOOK_SECRET_PATH") {
                Ok(v) => v,
                Err(_) => return Response::error("Configuration error: WEBHOOK_SECRET_PATH missing", 500),
            };

            let path_secret = match ctx.param("secret") {
                Some(p) => p,
                None => return Response::error("Unauthorized", 401),
            };
            if path_secret != &env_secret {
                return Response::error("Unauthorized", 401);
            }

            let update: crate::telegram::update::Update = match req.json().await {
                Ok(u) => u,
                Err(e) => {
                    tracing::error!("Failed to parse JSON: {}", e);
                    return Response::error("Bad request", 400);
                }
            };

            if let Some(msg) = update.message {
                let chat_id = msg.chat.id;
                let namespace = match ctx.env.durable_object("CHAT_STATE") {
                    Ok(ns) => ns,
                    Err(e) => return Response::error(format!("Durable Object namespace error: {}", e), 500),
                };
                let do_id = match namespace.id_from_name(&chat_id.to_string()) {
                    Ok(id) => id,
                    Err(e) => return Response::error(format!("Durable Object ID error: {}", e), 500),
                };
                let stub = match do_id.get_stub() {
                    Ok(s) => s,
                    Err(e) => return Response::error(format!("Durable Object Stub error: {}", e), 500),
                };

                let mut headers = Headers::new();
                headers.set("Content-Type", "application/json").unwrap();

                let payload = serde_json::to_string(&msg).unwrap();
                let do_req = match Request::new_with_init(
                    "http://durable/message",
                    &worker::RequestInit {
                        method: Method::Post,
                        headers,
                        body: Some(worker::wasm_bindgen::JsValue::from_str(&payload)),
                        ..Default::default()
                    },
                ) {
                    Ok(r) => r,
                    Err(e) => return Response::error(format!("DO request build error: {}", e), 500),
                };

                match stub.fetch_with_request(do_req).await {
                    Ok(mut resp) => {
                        let text = resp.text().await.unwrap_or_default();
                        Response::ok(text)
                    }
                    Err(e) => Response::error(format!("Durable Object fetch error: {}", e), 500),
                }
            } else {
                Response::ok("OK")
            }
        })
        .run(req, env)
        .await
}
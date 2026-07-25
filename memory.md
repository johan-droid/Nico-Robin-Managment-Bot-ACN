# Nico Robin Bot - Project Memory

## Project Overview
- **Name**: Nico Robin Bot
- **Version**: 0.2.0
- **Language**: Rust (2021 edition)
- **Framework**: worker 0.4 (Cloudflare Workers, wasm32-unknown-unknown)
- **Database**: PostgreSQL with tokio-postgres 0.7 (Hyperdrive over Wasm sockets)
- **Deployment**: Cloudflare Workers
- **Mode**: Webhook

## Current Status
**Last Updated**: 2026-07-22

### Architecture
- ✅ Rust backend with worker::fetch request handler
- ✅ Webhook execution replacing teloxide long-polling
- ✅ Raw tokio-postgres layer mapping query logic (sqlx fully removed)
- ✅ Role-based access control (Sudo > Captain > Commander > Normal)
- ✅ In-memory state caching moved to Cloudflare Durable Objects stub `ChatState`
- ✅ Centralized API wrap mimicking standard teloxide structures
- ✅ Built for wasm32-unknown-unknown natively

### Dependencies
- tokio 1.38 (macros only), worker 0.4, tokio-postgres 0.7 (js feature)
- serde 1.0, serde_json 1.0
- getrandom 0.2/0.4 (wasm_js)
- uuid 1.24.0 (v4, js)

### Database
- ✅ Migrations run via separate standalone bin `backend/src/bin/migrate.rs` using standard driver
- ✅ Tables: groups, notes, filters, warnings, welcome, profiles, swears, federations, features, flood

## Configuration
- Bot mode: webhook
- Environment variables: BOT_TOKEN, DATABASE_URL, WEBHOOK_SECRET_PATH

## Migration Instructions
1) Deploy Worker with webhook disabled.
2) Run migrate bin using raw Postgres URL.
3) Call setWebhook with proper worker subdomain and `WEBHOOK_SECRET_PATH`.
4) Monitor free tier caps (Hyperdrive <= 100k reads/day).

## Learnings
- **Cloudflare Workers Rust SDK**: When building for Wasm, native features like multi-thread, process, net, and io in `tokio` (which brings in `mio` and native epoll sockets) will break the Wasm build since they are unsupported. Strip `tokio` to `macros` and sync primitives.
- **tokio-postgres hyperdrive**: Requires specific Cloudflare worker's Hyperdrive-to-Socket configurations. The `sqlx` crate natively doesn't support Wasm, but `tokio-postgres` via the `devsnek` branch (or cloudflare socket examples) allows compilation down to `js`.
- **Randomness in Wasm**: Nested dependencies frequently resolve multiple versions of `getrandom`. Always explicitly enforce `getrandom` versions and their `wasm_js` / `js` features directly at the project root to solve overlapping RNG errors.
- **State in Webhooks**: State like rate limiting cannot persist safely in standard isolate memory across invocations natively. Use Durable Objects with an associated Router stub or external KV.

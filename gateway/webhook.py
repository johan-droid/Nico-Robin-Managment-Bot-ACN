"""Webhook gateway — hardened with API key protection, security headers, and size limits."""

from __future__ import annotations

import json
import secrets

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from telegram import Update
from telegram.ext import Application

from config import settings
from gateway.websocket import create_socketio_app, websocket_manager

UPDATE_COUNTER = Counter(
    "nico_robin_telegram_updates_total", "Total Telegram updates received."
)
UPDATE_LATENCY = Histogram(
    "nico_robin_update_processing_seconds", "Time processing updates."
)


# ── Security Headers Middleware ──
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


# ── Request Size Limit Middleware ──
MAX_BODY_SIZE = 1_048_576  # 1MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > MAX_BODY_SIZE:
            return Response("Payload too large", status_code=413)
        return await call_next(request)


def _check_api_key(key: str | None) -> None:
    """Validate metrics API key if configured."""
    if settings.metrics_api_key:
        if not key or not secrets.compare_digest(
            key, f"Bearer {settings.metrics_api_key}"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
            )


def create_app(ptb_app: Application) -> FastAPI:
    app = FastAPI(
        title="Nico Robin Bot", version="2.0.0", docs_url=None, redoc_url=None
    )
    app.state.ptb_app = ptb_app

    # Add security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok", "bot": settings.bot_name, "version": "2.0.0"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "bot": settings.bot_name}

    @app.get("/metrics")
    async def metrics(authorization: str | None = Header(default=None)) -> Response:
        _check_api_key(authorization)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/websocket/stats")
    async def ws_stats(authorization: str | None = Header(default=None)) -> dict:
        _check_api_key(authorization)
        return websocket_manager.get_connection_stats()

    @app.post("/webhook")
    async def webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, bool]:
        # Validate webhook secret
        if settings.webhook_secret and not secrets.compare_digest(
            x_telegram_bot_api_secret_token or "", settings.webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret"
            )
        # Validate payload size
        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            raise HTTPException(status_code=413, detail="Payload too large")
        try:

            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise HTTPException(status_code=400, detail="Invalid JSON") from e
        # Validate it looks like a Telegram update
        if not isinstance(payload, dict) or "update_id" not in payload:
            raise HTTPException(status_code=400, detail="Invalid update format")
        update = Update.de_json(payload, ptb_app.bot)
        UPDATE_COUNTER.inc()
        with UPDATE_LATENCY.time():
            await ptb_app.process_update(update)
        return {"ok": True}

    return app


def create_combined_app(ptb_app: Application):
    fastapi_app = create_app(ptb_app)
    socketio_app = create_socketio_app(other_asgi_app=fastapi_app)
    return socketio_app

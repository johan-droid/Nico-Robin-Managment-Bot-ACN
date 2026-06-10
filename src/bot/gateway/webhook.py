"""Webhook gateway — hardened with API key protection, security headers, and size limits."""

from __future__ import annotations

import json
import secrets
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from telegram import Update
from telegram.ext import Application

from src.bot.config import settings
from src.bot.gateway.websocket import create_socketio_app, websocket_manager

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


def _validate_webhook_auth(
    *,
    header_secret: str | None,
    path_token: str | None = None,
) -> None:
    """Validate Telegram webhook auth using header and optional path token."""
    configured_secret = settings.webhook_secret.strip()
    configured_path_token = settings.webhook_path_token.strip()

    if configured_path_token and not secrets.compare_digest(
        path_token or "", configured_path_token
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook path token"
        )

    if not configured_secret:
        return

    if not settings.webhook_require_secret_header:
        return

    if not secrets.compare_digest(header_secret or "", configured_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret"
        )


async def _process_telegram_update(
    *,
    request: Request,
    ptb_app: Application,
) -> dict[str, bool]:
    body = await request.body()
    if len(body) > MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        payload: Any = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    if not isinstance(payload, dict) or "update_id" not in payload:
        raise HTTPException(status_code=400, detail="Invalid update format")
    update = Update.de_json(payload, ptb_app.bot)
    UPDATE_COUNTER.inc()
    with UPDATE_LATENCY.time():
        await ptb_app.process_update(update)
    return {"ok": True}


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

    @app.head("/")
    async def root_head() -> Response:
        return Response(status_code=status.HTTP_200_OK)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "bot": settings.bot_name}

    @app.head("/health")
    async def health_head() -> Response:
        return Response(status_code=status.HTTP_200_OK)

    @app.get("/diagnostics")
    async def diagnostics() -> dict[str, Any]:
        return {
            "bot_mode": settings.bot_mode,
            "environment": settings.environment,
            "webhook_base_url_present": bool(settings.resolved_webhook_url),
            "webhook_path": settings.webhook_path,
            "webhook_secret_configured": bool(settings.webhook_secret),
            "services": {
                "database_configured": bool(settings.database_url),
                "redis_configured": bool(settings.redis_url),
                "celery_broker_configured": bool(settings.celery_broker_url),
                "celery_backend_configured": bool(settings.celery_result_backend),
            },
            "ai_moderation_enabled": settings.ai_moderation_enabled,
            "moderation_provider": settings.moderation_provider,
        }


    @app.get("/metrics")
    async def metrics(authorization: str | None = Header(default=None)) -> Response:
        _check_api_key(authorization)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/websocket/stats")
    async def ws_stats(authorization: str | None = Header(default=None)) -> dict:
        _check_api_key(authorization)
        return websocket_manager.get_connection_stats()

    async def webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, bool]:
        _validate_webhook_auth(
            header_secret=x_telegram_bot_api_secret_token,
        )
        return await _process_telegram_update(request=request, ptb_app=ptb_app)

    async def webhook_with_token(
        request: Request,
        path_token: str,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, bool]:
        _validate_webhook_auth(
            header_secret=x_telegram_bot_api_secret_token,
            path_token=path_token,
        )
        return await _process_telegram_update(request=request, ptb_app=ptb_app)

    webhook_paths = {
        settings.webhook_path,
        "/webhook",
        "/telegram/webhook",
    }
    for webhook_path in webhook_paths:
        app.add_api_route(webhook_path, webhook, methods=["POST"])
        app.add_api_route(
            f"{webhook_path.rstrip('/')}/{{path_token}}",
            webhook_with_token,
            methods=["POST"],
        )

    @app.get("/webhook")
    @app.get("/telegram/webhook")
    async def webhook_probe() -> dict[str, str]:
        return {
            "status": "ok",
            "message": "Use POST with a Telegram Update JSON body to trigger the bot.",
        }

    return app


def create_combined_app(ptb_app: Application):
    fastapi_app = create_app(ptb_app)
    socketio_app = create_socketio_app(other_asgi_app=fastapi_app)
    return socketio_app

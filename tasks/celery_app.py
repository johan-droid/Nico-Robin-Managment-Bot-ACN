from __future__ import annotations

from celery import Celery

from config import settings

celery_app = Celery(
    "nico_robin",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.ban_tasks", "tasks.announce_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

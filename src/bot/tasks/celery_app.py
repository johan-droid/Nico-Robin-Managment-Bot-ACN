from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.bot.config import settings

_DEFAULT_BROKER_URL = "memory://"
_DEFAULT_RESULT_BACKEND = "cache+memory://"

broker_url = settings.celery_broker_url or _DEFAULT_BROKER_URL
result_backend = settings.celery_result_backend or _DEFAULT_RESULT_BACKEND

celery_app = Celery(
    "nico_robin",
    broker=broker_url,
    backend=result_backend,
    include=[
        "src.bot.tasks.ban_tasks",
        "src.bot.tasks.announce_tasks",
        "src.bot.tasks.nightmode_tasks",
    ],
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

celery_app.conf.beat_schedule = {
    "nightmode-lock": {
        "task": "src.bot.tasks.nightmode_tasks.lock_group_task",
        "schedule": crontab(hour=0, minute=0),
    },
    "nightmode-unlock": {
        "task": "src.bot.tasks.nightmode_tasks.unlock_group_task",
        "schedule": crontab(hour=6, minute=0),
    },
}

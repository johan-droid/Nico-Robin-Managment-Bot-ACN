release: alembic upgrade head
web: python -m src.bot.main
worker: celery -A src.bot.tasks.celery_app:celery_app worker --loglevel=info
beat: celery -A src.bot.tasks.celery_app:celery_app beat --loglevel=info

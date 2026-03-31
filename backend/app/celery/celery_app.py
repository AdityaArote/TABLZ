"""
TABLZ — Celery app configuration.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "tablz",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.celery.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min hard limit
    task_soft_time_limit=240,  # 4 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "reset-daily-specials": {
        "task": "app.celery.tasks.reset_daily_specials",
        "schedule": {
            "hour": 0,
            "minute": 0,
        },
    },
}

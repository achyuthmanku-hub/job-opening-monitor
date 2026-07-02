import os

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

from src.config import ROOT

load_dotenv(ROOT / ".env")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "job_monitor",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

# Hourly pipeline: scan -> parse -> embed -> alerts
celery_app.conf.beat_schedule = {
    "hourly-scan": {
        "task": "api.tasks.scan_all_companies",
        "schedule": crontab(minute=0),
        "kwargs": {"store_all": False, "enrich": True, "parse_nlp": True},
    },
    "hourly-embed": {
        "task": "api.tasks.embed_new_jobs",
        "schedule": crontab(minute=15),
        "kwargs": {"limit": 200},
    },
    "hourly-alerts": {
        "task": "api.tasks.send_alerts",
        "schedule": crontab(minute=30),
        "kwargs": {"dry_run": False},
    },
}

"""Background tasks for scan, parse, embed, and alerts."""

from __future__ import annotations

import logging
from typing import Optional

from api.celery_app import celery_app
from api.services.alerts import run_alerts
from api.services.descriptions import enrich_descriptions
from api.services.ingest import ingest_jobs
from api.services.nlp_pipeline import parse_jobs
from api.services.rag_pipeline import embed_jobs, embed_profile
from src.config import load_settings
from src.db import SessionLocal

logger = logging.getLogger(__name__)


def _db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@celery_app.task(name="api.tasks.scan_all_companies", bind=True)
def scan_all_companies(
    self,
    *,
    store_all: bool = False,
    enrich: bool = True,
    parse_nlp: bool = True,
    description_limit: int = 100,
    parse_limit: int = 200,
) -> dict:
    settings = load_settings()
    db = SessionLocal()
    try:
        summary = ingest_jobs(db, settings, store_all=store_all)
        if enrich:
            summary["descriptions_enriched"] = enrich_descriptions(db, limit=description_limit)
        if parse_nlp:
            parse_summary = parse_jobs(db, limit=parse_limit)
            summary["jobs_parsed"] = parse_summary["parsed"]
        logger.info("scan_all_companies complete: %s", summary)
        return summary
    finally:
        db.close()


@celery_app.task(name="api.tasks.parse_new_jobs")
def parse_new_jobs_task(*, limit: int = 200) -> dict:
    db = SessionLocal()
    try:
        return parse_jobs(db, limit=limit)
    finally:
        db.close()


@celery_app.task(name="api.tasks.embed_new_jobs")
def embed_new_jobs_task(*, profile_id: Optional[int] = None, limit: int = 200) -> dict:
    db = SessionLocal()
    try:
        job_summary = embed_jobs(db, limit=limit, only_unembedded=True)
        profile_summary = None
        if profile_id is not None:
            profile_summary = embed_profile(db, profile_id, force=False)
        return {"jobs": job_summary, "profile": profile_summary}
    finally:
        db.close()


@celery_app.task(name="api.tasks.send_alerts")
def send_alerts_task(*, dry_run: bool = False) -> dict:
    settings = load_settings()
    db = SessionLocal()
    try:
        return run_alerts(db, settings, dry_run=dry_run)
    finally:
        db.close()

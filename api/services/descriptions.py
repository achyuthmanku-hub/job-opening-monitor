"""Fetch and store full job descriptions for jobs in the database."""

import logging

from sqlalchemy.orm import Session, joinedload

from src.apply.job_description import fetch_job_description
from src.config import load_settings
from src.db.models import Job
from src.models import JobPosting

logger = logging.getLogger(__name__)


def enrich_descriptions(db: Session, *, limit: int = 100) -> int:
    settings = load_settings()
    jobs = db.query(Job).options(joinedload(Job.company)).limit(limit * 3).all()
    candidates = [
        job
        for job in jobs
        if not job.description or len((job.description or "").strip()) < 150
    ][:limit]

    updated = 0
    for job in candidates:
        posting = JobPosting(
            company=job.company.name if job.company else "",
            title=job.title,
            url=job.url,
            source=job.source,
            location=job.location,
            posted_at=job.posted_at,
        )
        text = fetch_job_description(posting, settings).strip()
        if text and text != job.description:
            job.description = text[:12000]
            updated += 1
    if updated:
        db.commit()
    logger.info("Enriched descriptions for %d job(s).", updated)
    return updated

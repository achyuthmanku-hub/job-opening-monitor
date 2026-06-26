import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from src.db.models import Job, SeenJob
from src.filters import job_matches_filters
from src.models import JobPosting
from src.notifier import send_email

logger = logging.getLogger(__name__)


def _to_posting(job: Job) -> JobPosting:
    return JobPosting(
        company=job.company.name if job.company else "",
        title=job.title,
        url=job.url,
        source=job.source,
        location=job.location,
        posted_at=job.posted_at,
    )


def get_new_jobs(db: Session, settings: dict) -> list[Job]:
    rows = (
        db.query(Job)
        .options(joinedload(Job.company), joinedload(Job.seen))
        .all()
    )
    new_jobs: list[Job] = []
    for job in rows:
        if job.seen is not None:
            continue
        posting = _to_posting(job)
        if job_matches_filters(posting, settings):
            new_jobs.append(job)
    return new_jobs


def run_alerts(db: Session, settings: dict, *, dry_run: bool = False) -> dict:
    new_jobs = get_new_jobs(db, settings)
    if not new_jobs:
        return {"new_jobs": 0, "emailed": 0}

    postings = [_to_posting(job) for job in new_jobs]
    if dry_run:
        return {
            "new_jobs": len(new_jobs),
            "emailed": 0,
            "dry_run": True,
            "titles": [f"{p.company} — {p.title}" for p in postings[:20]],
        }

    send_email(postings, settings["smtp"])
    now = datetime.now(timezone.utc)
    for job in new_jobs:
        seen = job.seen
        if seen is None:
            seen = SeenJob(job_id=job.id)
            db.add(seen)
        seen.notified_at = now
    db.commit()
    logger.info("Alert email sent for %d job(s).", len(new_jobs))
    return {"new_jobs": len(new_jobs), "emailed": len(new_jobs)}

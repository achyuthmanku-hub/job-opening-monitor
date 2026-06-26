import json
import logging

from sqlalchemy.orm import Session, joinedload

from src.db.models import Job, JobParsed
from src.nlp.jd_parser import parse_job_description, parsed_to_json

logger = logging.getLogger(__name__)


def parse_job_record(job: Job) -> JobParsed:
    parsed = parse_job_description(job.title, job.description or "")
    row = job.parsed
    if row is None:
        row = JobParsed(job_id=job.id)
    row.skills_json = parsed_to_json(parsed)
    row.seniority = parsed.seniority
    row.min_years = parsed.min_years
    row.max_years = parsed.max_years
    row.requires_clearance = parsed.requires_clearance
    row.sponsorship_mentioned = parsed.sponsorship_mentioned
    return row


def parse_jobs(db: Session, *, limit: int = 100, only_unparsed: bool = True) -> dict:
    query = db.query(Job).options(joinedload(Job.parsed))
    if only_unparsed:
        query = query.outerjoin(JobParsed).filter(JobParsed.id.is_(None))
    jobs = query.limit(limit).all()

    parsed_count = 0
    skipped = 0
    for job in jobs:
        if only_unparsed and job.parsed is not None:
            skipped += 1
            continue
        row = parse_job_record(job)
        if job.parsed is None:
            db.add(row)
        parsed_count += 1
    db.commit()
    logger.info("NLP parsed %d job(s), skipped %d.", parsed_count, skipped)
    return {"parsed": parsed_count, "skipped": skipped}


def parsed_skills(row: JobParsed) -> list[str]:
    try:
        return json.loads(row.skills_json or "[]")
    except json.JSONDecodeError:
        return []

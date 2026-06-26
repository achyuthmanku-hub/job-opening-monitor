import logging
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from src.db.models import Company, Job
from src.filters import job_matches_filters
from src.models import JobPosting
from src.monitor import fetch_all_jobs

logger = logging.getLogger(__name__)


def _parse_source(source: str) -> tuple[str, str]:
    if ":" not in source:
        return source, ""
    ats, rest = source.split(":", 1)
    slug = rest.split("/")[0] if rest else ""
    return ats, slug


def _careers_url(job: JobPosting) -> str:
    parsed = urlparse(job.url)
    if not parsed.scheme:
        return job.url
    return f"{parsed.scheme}://{parsed.netloc}"


def _get_or_create_company(db: Session, job: JobPosting) -> Company:
    company = db.query(Company).filter(Company.name == job.company).one_or_none()
    ats_type, slug = _parse_source(job.source)
    careers_url = _careers_url(job)
    if company is None:
        company = Company(
            name=job.company,
            ats_type=ats_type,
            slug=slug,
            careers_url=careers_url,
        )
        db.add(company)
        db.flush()
        return company
    if not company.ats_type and ats_type:
        company.ats_type = ats_type
    if not company.slug and slug:
        company.slug = slug
    if not company.careers_url and careers_url:
        company.careers_url = careers_url
    return company


def upsert_job(db: Session, posting: JobPosting) -> tuple[Job, bool]:
    company = _get_or_create_company(db, posting)
    job_key = posting.id
    existing = db.query(Job).filter(Job.job_key == job_key).one_or_none()
    description = f"{posting.title}\n{posting.location}".strip()
    if existing:
        existing.title = posting.title
        existing.location = posting.location or existing.location
        existing.posted_at = posting.posted_at or existing.posted_at
        existing.source = posting.source
        if not existing.description:
            existing.description = description
        return existing, False

    job = Job(
        job_key=job_key,
        company_id=company.id,
        title=posting.title,
        url=posting.url,
        location=posting.location or "",
        source=posting.source,
        description=description,
        posted_at=posting.posted_at or "",
    )
    db.add(job)
    db.flush()
    return job, True


def ingest_jobs(db: Session, settings: dict, *, store_all: bool = False) -> dict:
    fetched = fetch_all_jobs(settings)
    if store_all:
        candidates = fetched
    else:
        candidates = [job for job in fetched if job_matches_filters(job, settings)]

    created = 0
    updated = 0
    for posting in candidates:
        _, is_new = upsert_job(db, posting)
        if is_new:
            created += 1
        else:
            updated += 1
    db.commit()

    summary = {
        "fetched": len(fetched),
        "stored": len(candidates),
        "created": created,
        "updated": updated,
    }
    logger.info("Ingest complete: %s", summary)
    return summary

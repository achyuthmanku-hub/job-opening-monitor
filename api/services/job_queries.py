from typing import Optional

from sqlalchemy.orm import Session, joinedload

from api.schemas.jobs import JobOut, JobParsedOut
from api.services.nlp_pipeline import parsed_skills
from src.db.models import Company, Job, JobParsed


def job_to_schema(job: Job) -> JobOut:
    parsed_out = None
    if job.parsed is not None:
        parsed_out = JobParsedOut(
            skills=parsed_skills(job.parsed),
            seniority=job.parsed.seniority,
            min_years=job.parsed.min_years,
            max_years=job.parsed.max_years,
            requires_clearance=job.parsed.requires_clearance,
            sponsorship_mentioned=job.parsed.sponsorship_mentioned,
            parsed_at=job.parsed.parsed_at,
        )
    preview = (job.description or "")[:280]
    return JobOut(
        id=job.id,
        job_key=job.job_key,
        company=job.company.name if job.company else "",
        title=job.title,
        url=job.url,
        location=job.location,
        source=job.source,
        posted_at=job.posted_at,
        description_preview=preview,
        is_seen=job.seen is not None,
        parsed=parsed_out,
    )


def query_jobs(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    company: Optional[str] = None,
    keyword: Optional[str] = None,
    seniority: Optional[str] = None,
    skill: Optional[str] = None,
    unseen_only: bool = False,
) -> tuple[int, list[JobOut]]:
    query = (
        db.query(Job)
        .options(
            joinedload(Job.company),
            joinedload(Job.parsed),
            joinedload(Job.seen),
        )
        .join(Job.company)
        .outerjoin(JobParsed)
        .outerjoin(Job.seen)
    )

    if company:
        query = query.filter(Company.name == company)
    if keyword:
        like = f"%{keyword.lower()}%"
        query = query.filter(Job.title.ilike(like))
    if seniority:
        query = query.filter(JobParsed.seniority == seniority.lower())
    if skill:
        query = query.filter(JobParsed.skills_json.ilike(f"%{skill.lower()}%"))
    if unseen_only:
        query = query.filter(Job.seen == None)  # noqa: E711

    total = query.count()
    rows = (
        query.order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, [job_to_schema(job) for job in rows]

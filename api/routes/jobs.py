from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas.jobs import AlertResponse, JobListResponse, JobOut, ParseResponse, ScanRequest, ScanResponse
from api.services.alerts import get_new_jobs, run_alerts
from api.services.descriptions import enrich_descriptions
from api.services.ingest import ingest_jobs
from api.services.job_queries import job_to_schema, query_jobs
from api.services.nlp_pipeline import parse_jobs, parsed_skills
from src.config import load_settings
from src.db import get_db
from src.db.models import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/scan", response_model=ScanResponse)
def scan_jobs(body: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    settings = load_settings()
    summary = ingest_jobs(db, settings, store_all=body.store_all)
    descriptions_enriched = 0
    jobs_parsed = 0
    if body.enrich_descriptions:
        descriptions_enriched = enrich_descriptions(db, limit=body.description_limit)
    if body.parse_nlp:
        parse_summary = parse_jobs(db, limit=body.parse_limit)
        jobs_parsed = parse_summary["parsed"]
    return ScanResponse(
        **summary,
        descriptions_enriched=descriptions_enriched,
        jobs_parsed=jobs_parsed,
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    company: Optional[str] = None,
    keyword: Optional[str] = None,
    seniority: Optional[str] = None,
    skill: Optional[str] = None,
    db: Session = Depends(get_db),
) -> JobListResponse:
    total, jobs = query_jobs(
        db,
        limit=limit,
        offset=offset,
        company=company,
        keyword=keyword,
        seniority=seniority,
        skill=skill,
    )
    return JobListResponse(total=total, jobs=jobs)


@router.get("/new", response_model=JobListResponse)
def list_new_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> JobListResponse:
    settings = load_settings()
    rows = get_new_jobs(db, settings)[:limit]
    jobs = [job_to_schema(job) for job in rows]
    return JobListResponse(total=len(jobs), jobs=jobs)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    from sqlalchemy.orm import joinedload

    job = (
        db.query(Job)
        .options(joinedload(Job.company), joinedload(Job.parsed), joinedload(Job.seen))
        .filter(Job.id == job_id)
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_schema(job)


@router.get("/{job_id}/parsed")
def get_job_parsed(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if job is None or job.parsed is None:
        raise HTTPException(status_code=404, detail="Parsed job data not found")
    parsed = job.parsed
    return {
        "job_id": job_id,
        "skills": parsed_skills(parsed),
        "seniority": parsed.seniority,
        "min_years": parsed.min_years,
        "max_years": parsed.max_years,
        "requires_clearance": parsed.requires_clearance,
        "sponsorship_mentioned": parsed.sponsorship_mentioned,
        "parsed_at": parsed.parsed_at,
    }

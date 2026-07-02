from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from api.deps.auth import require_user
from api.schemas.jobs import ProfileCreate, ProfileOut
from api.schemas.rag import EmbedResponse, MatchDetailResponse, MatchListResponse, MatchItem
from api.services.rag_pipeline import (
    embed_jobs,
    embed_profile,
    load_json_list,
    match_profile_to_job,
    match_profile_to_jobs,
)
from src.db import get_db
from src.db.models import Job, JobMatch, Profile, User

router = APIRouter(tags=["profiles"])


@router.post("/profiles", response_model=ProfileOut)
def create_profile(
    body: ProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProfileOut:
    profile = Profile(
        name=body.name,
        resume_text=body.resume_text,
        preferences_json=body.preferences_json,
        user_id=user.id if user.id else None,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)) -> list[ProfileOut]:
    return db.query(Profile).order_by(Profile.created_at.desc()).all()


@router.post("/profiles/{profile_id}/embed", response_model=EmbedResponse)
def embed_profile_endpoint(
    profile_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> EmbedResponse:
    try:
        result = embed_profile(db, profile_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EmbedResponse(**result)


@router.post("/jobs/embed", response_model=EmbedResponse)
def embed_jobs_endpoint(
    limit: int = Query(default=500, ge=1, le=2000),
    only_unembedded: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> EmbedResponse:
    result = embed_jobs(db, limit=limit, only_unembedded=only_unembedded)
    return EmbedResponse(jobs_embedded=result["jobs_embedded"], chunks=result["chunks"])


@router.get("/profiles/{profile_id}/matches", response_model=MatchListResponse)
def list_profile_matches(
    profile_id: int,
    min_score: float = Query(default=70.0, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=200),
    mode: str = Query(default="auto"),
    use_llm: bool = Query(default=True),
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> MatchListResponse:
    if refresh:
        try:
            result = match_profile_to_jobs(
                db,
                profile_id,
                min_score=min_score,
                limit=limit,
                mode=mode,
                use_llm=use_llm,
                store=True,
            )
            return MatchListResponse(**result)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    rows = (
        db.query(JobMatch)
        .filter(JobMatch.profile_id == profile_id, JobMatch.score >= min_score)
        .order_by(JobMatch.score.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        try:
            result = match_profile_to_jobs(
                db,
                profile_id,
                min_score=min_score,
                limit=limit,
                mode=mode,
                use_llm=use_llm,
                store=True,
            )
            return MatchListResponse(**result)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    job_ids = [row.job_id for row in rows]
    jobs = {
        job.id: job
        for job in db.query(Job)
        .options(joinedload(Job.company))
        .filter(Job.id.in_(job_ids))
        .all()
    }
    matches = []
    for row in rows:
        job = jobs.get(row.job_id)
        if not job:
            continue
        matches.append(
            MatchItem(
                job_id=row.job_id,
                company=job.company.name if job.company else "",
                title=job.title,
                url=job.url,
                score=row.score,
                summary=row.summary,
                strengths=load_json_list(row.strengths_json),
                gaps=load_json_list(row.gaps_json),
                evidence=load_json_list(row.evidence_json),
            )
        )
    return MatchListResponse(profile_id=profile_id, matched=len(matches), matches=matches)


@router.get(
    "/profiles/{profile_id}/matches/{job_id}",
    response_model=MatchDetailResponse,
)
def get_profile_job_match(
    profile_id: int,
    job_id: int,
    mode: str = Query(default="auto"),
    use_llm: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> MatchDetailResponse:
    try:
        result = match_profile_to_job(
            db,
            profile_id,
            job_id,
            mode=mode,
            use_llm=use_llm,
            store=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MatchDetailResponse(profile_id=profile_id, **result)

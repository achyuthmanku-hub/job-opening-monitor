"""Embed jobs/profiles and compute RAG matches."""

import json
import logging

from sqlalchemy.orm import Session, joinedload

from src.db.models import Job, JobChunk, Profile, ResumeChunk
from src.rag.chunker import chunk_job, chunk_resume
from src.rag.embedder import embed_texts, embedding_to_json
from src.rag.matcher import match_job_for_profile, upsert_job_match

logger = logging.getLogger(__name__)


def embed_profile(db: Session, profile_id: int, *, force: bool = False) -> dict:
    profile = db.query(Profile).filter(Profile.id == profile_id).one_or_none()
    if profile is None:
        raise ValueError(f"Profile {profile_id} not found")

    existing = db.query(ResumeChunk).filter(ResumeChunk.profile_id == profile_id).count()
    if existing and not force:
        return {"profile_id": profile_id, "chunks": existing, "skipped": True}

    if force:
        db.query(ResumeChunk).filter(ResumeChunk.profile_id == profile_id).delete()

    texts = chunk_resume(profile.resume_text)
    if not texts:
        return {"profile_id": profile_id, "chunks": 0, "skipped": False}

    vectors = embed_texts(texts)
    for index, (text, vector) in enumerate(zip(texts, vectors)):
        db.add(
            ResumeChunk(
                profile_id=profile_id,
                chunk_index=index,
                chunk_text=text,
                embedding_json=embedding_to_json(vector),
            )
        )
    db.commit()
    logger.info("Embedded profile %d with %d chunk(s).", profile_id, len(texts))
    return {"profile_id": profile_id, "chunks": len(texts), "skipped": False}


def embed_job(db: Session, job_id: int, *, force: bool = False) -> dict:
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    existing = db.query(JobChunk).filter(JobChunk.job_id == job_id).count()
    if existing and not force:
        return {"job_id": job_id, "chunks": existing, "skipped": True}

    if force or existing:
        db.query(JobChunk).filter(JobChunk.job_id == job_id).delete()

    texts = chunk_job(job.title, job.description or "", job.location or "")
    if not texts:
        return {"job_id": job_id, "chunks": 0, "skipped": False}

    vectors = embed_texts(texts)
    for index, (text, vector) in enumerate(zip(texts, vectors)):
        db.add(
            JobChunk(
                job_id=job.id,
                chunk_index=index,
                chunk_text=text,
                embedding_json=embedding_to_json(vector),
            )
        )
    db.commit()
    return {"job_id": job_id, "chunks": len(texts), "skipped": False}


def embed_jobs(db: Session, *, limit: int = 500, only_unembedded: bool = True) -> dict:
    query = db.query(Job).options(joinedload(Job.company))
    if only_unembedded:
        query = query.outerjoin(JobChunk).filter(JobChunk.id.is_(None))
    jobs = query.limit(limit).all()

    embedded_jobs = 0
    total_chunks = 0
    for job in jobs:
        if only_unembedded:
            has_chunks = (
                db.query(JobChunk.id).filter(JobChunk.job_id == job.id).limit(1).first()
            )
            if has_chunks:
                continue

        db.query(JobChunk).filter(JobChunk.job_id == job.id).delete()
        texts = chunk_job(job.title, job.description or "", job.location or "")
        if not texts:
            continue
        vectors = embed_texts(texts)
        for index, (text, vector) in enumerate(zip(texts, vectors)):
            db.add(
                JobChunk(
                    job_id=job.id,
                    chunk_index=index,
                    chunk_text=text,
                    embedding_json=embedding_to_json(vector),
                )
            )
        embedded_jobs += 1
        total_chunks += len(texts)

    db.commit()
    logger.info("Embedded %d job(s), %d chunk(s).", embedded_jobs, total_chunks)
    return {"jobs_embedded": embedded_jobs, "chunks": total_chunks}


def match_profile_to_jobs(
    db: Session,
    profile_id: int,
    *,
    min_score: float = 70.0,
    limit: int = 50,
    mode: str = "auto",
    use_llm: bool = True,
    store: bool = True,
) -> dict:
    profile = db.query(Profile).filter(Profile.id == profile_id).one_or_none()
    if profile is None:
        raise ValueError(f"Profile {profile_id} not found")

    resume_chunk_count = (
        db.query(ResumeChunk).filter(ResumeChunk.profile_id == profile_id).count()
    )
    if resume_chunk_count == 0:
        embed_profile(db, profile_id)

    job_chunk_count = db.query(JobChunk.id).limit(1).first()
    if job_chunk_count is None:
        embed_jobs(db, limit=500, only_unembedded=False)

    jobs = db.query(Job).options(joinedload(Job.company)).all()
    results = []
    for job in jobs:
        result = match_job_for_profile(
            db, profile, job, mode=mode, use_llm=use_llm
        )
        if result.score < min_score:
            continue
        if store:
            upsert_job_match(db, profile_id, job.id, result)
        results.append(
            {
                "job_id": job.id,
                "company": job.company.name if job.company else "",
                "title": job.title,
                "url": job.url,
                "score": result.score,
                "summary": result.summary,
                "strengths": result.strengths,
                "gaps": result.gaps,
                "evidence": result.evidence,
            }
        )

    if store:
        db.commit()

    results.sort(key=lambda item: item["score"], reverse=True)
    return {
        "profile_id": profile_id,
        "matched": len(results),
        "matches": results[:limit],
    }


def match_profile_to_job(
    db: Session,
    profile_id: int,
    job_id: int,
    *,
    mode: str = "auto",
    use_llm: bool = True,
    store: bool = True,
) -> dict:
    profile = db.query(Profile).filter(Profile.id == profile_id).one_or_none()
    job = db.query(Job).options(joinedload(Job.company)).filter(Job.id == job_id).one_or_none()
    if profile is None or job is None:
        raise ValueError("Profile or job not found")

    if db.query(ResumeChunk).filter(ResumeChunk.profile_id == profile_id).count() == 0:
        embed_profile(db, profile_id)
    if db.query(JobChunk).filter(JobChunk.job_id == job_id).count() == 0:
        embed_job(db, job_id)

    result = match_job_for_profile(db, profile, job, mode=mode, use_llm=use_llm)
    if store:
        upsert_job_match(db, profile_id, job_id, result)
        db.commit()

    return {
        "profile_id": profile_id,
        "job_id": job_id,
        "company": job.company.name if job.company else "",
        "title": job.title,
        "url": job.url,
        "score": result.score,
        "summary": result.summary,
        "strengths": result.strengths,
        "gaps": result.gaps,
        "evidence": result.evidence,
    }


def load_json_list(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

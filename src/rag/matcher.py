"""RAG-style matching: vector retrieval + optional LLM explanation."""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from src.apply.match_score import score_resume_match
from src.db.models import Job, JobChunk, JobMatch, Profile, ResumeChunk

from .embedder import embedding_from_json

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    score: float
    summary: str
    strengths: list[str]
    gaps: list[str]
    evidence: list[str]


def _chunk_vectors(chunks: list) -> list[np.ndarray]:
    vectors = []
    for chunk in chunks:
        vector = embedding_from_json(chunk.embedding_json)
        if vector is not None:
            vectors.append(vector)
    return vectors


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def vector_match_score(resume_vectors: list[np.ndarray], job_vectors: list[np.ndarray]) -> float:
    if not resume_vectors or not job_vectors:
        return 0.0

    best_scores: list[float] = []
    for job_vector in job_vectors:
        similarities = [_cosine_similarity(job_vector, resume_vector) for resume_vector in resume_vectors]
        best_scores.append(max(similarities))

    # Weight top job-chunk matches (RAG retrieval style).
    best_scores.sort(reverse=True)
    top = best_scores[: min(3, len(best_scores))]
    raw = sum(top) / len(top)
    return round(max(0.0, min(100.0, raw * 100)), 1)


def _evidence_chunks(
    resume_chunks: list[ResumeChunk],
    job_chunks: list[JobChunk],
    resume_vectors: list[np.ndarray],
    job_vectors: list[np.ndarray],
    *,
    limit: int = 3,
) -> list[str]:
    if not resume_chunks or not job_chunks:
        return []

    pairs: list[tuple[float, str]] = []
    for job_index, job_vector in enumerate(job_vectors):
        for resume_index, resume_vector in enumerate(resume_vectors):
            score = _cosine_similarity(job_vector, resume_vector)
            text = resume_chunks[resume_index].chunk_text[:220]
            pairs.append((score, text))

    pairs.sort(key=lambda item: item[0], reverse=True)
    seen: set[str] = set()
    evidence: list[str] = []
    for _, text in pairs:
        if text in seen:
            continue
        seen.add(text)
        evidence.append(text)
        if len(evidence) >= limit:
            break
    return evidence


def _local_summary(score: float, evidence: list[str]) -> tuple[str, list[str], list[str]]:
    if not evidence:
        return (
            f"Vector similarity match ({score:.0f}%).",
            [],
            [],
        )
    strengths = [line[:120] for line in evidence[:2]]
    return (
        f"Resume evidence aligns at {score:.0f}% based on {len(evidence)} retrieved chunk(s).",
        strengths,
        [],
    )


def match_job_for_profile(
    db: Session,
    profile: Profile,
    job: Job,
    *,
    mode: str = "auto",
    use_llm: bool = True,
) -> MatchResult:
    resume_chunks = (
        db.query(ResumeChunk)
        .filter(ResumeChunk.profile_id == profile.id)
        .order_by(ResumeChunk.chunk_index)
        .all()
    )
    job_chunks = (
        db.query(JobChunk).filter(JobChunk.job_id == job.id).order_by(JobChunk.chunk_index).all()
    )

    resume_vectors = _chunk_vectors(resume_chunks)
    job_vectors = _chunk_vectors(job_chunks)
    vector_score = vector_match_score(resume_vectors, job_vectors)
    evidence = _evidence_chunks(resume_chunks, job_chunks, resume_vectors, job_vectors)

    summary = ""
    strengths: list[str] = []
    gaps: list[str] = []

    if use_llm and mode in ("auto", "openai") and profile.resume_text.strip():
        try:
            llm_score, llm_summary = score_resume_match(
                profile.resume_text,
                job.title,
                job.description or "",
                mode=mode,
            )
            # Blend vector retrieval with LLM judgment.
            score = round(vector_score * 0.45 + llm_score * 0.55, 1)
            summary = llm_summary
            if evidence:
                strengths = [evidence[0][:120]]
        except Exception as exc:
            logger.warning("LLM match failed for job %s: %s", job.id, exc)
            score = vector_score
            summary, strengths, gaps = _local_summary(score, evidence)
    else:
        score = vector_score
        summary, strengths, gaps = _local_summary(score, evidence)

    return MatchResult(
        score=score,
        summary=summary,
        strengths=strengths,
        gaps=gaps,
        evidence=evidence,
    )


def upsert_job_match(db: Session, profile_id: int, job_id: int, result: MatchResult) -> JobMatch:
    row = (
        db.query(JobMatch)
        .filter(JobMatch.profile_id == profile_id, JobMatch.job_id == job_id)
        .one_or_none()
    )
    payload = {
        "score": result.score,
        "summary": result.summary,
        "strengths_json": json.dumps(result.strengths),
        "gaps_json": json.dumps(result.gaps),
        "evidence_json": json.dumps(result.evidence),
    }
    if row is None:
        row = JobMatch(profile_id=profile_id, job_id=job_id, **payload)
        db.add(row)
    else:
        row.score = payload["score"]
        row.summary = payload["summary"]
        row.strengths_json = payload["strengths_json"]
        row.gaps_json = payload["gaps_json"]
        row.evidence_json = payload["evidence_json"]
    return row

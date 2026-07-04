"""Onboard a user from an uploaded resume and compute personalized matches."""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from api.services.rag_pipeline import embed_profile, match_profile_to_jobs
from src.db.models import Profile

logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def extract_resume_text(filename: str, data: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document

        document = Document(io.BytesIO(data))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    elif suffix in {".txt", ".md"}:
        text = data.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type. Upload PDF, DOCX, or TXT.")

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 80:
        raise ValueError(
            "Could not read enough text from the resume. Try a text-based PDF or paste text."
        )
    return text


def guess_name_from_resume(text: str, fallback: str = "Candidate") -> str:
    for line in text.splitlines()[:8]:
        cleaned = line.strip()
        if not cleaned or len(cleaned) > 60:
            continue
        if "@" in cleaned or "http" in cleaned.lower():
            continue
        if re.search(r"\d{3}[-.\s]?\d{3}", cleaned):
            continue
        if re.match(r"^[A-Za-z][A-Za-z\s.'-]{1,50}$", cleaned):
            return cleaned.title()
    return fallback


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or "resume.pdf"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload PDF, DOCX, or TXT.")
    data = await file.read()
    if not data:
        raise ValueError("Empty file uploaded.")
    if len(data) > MAX_RESUME_BYTES:
        raise ValueError("Resume file is too large (max 5 MB).")
    return filename, data


def onboard_resume(
    db: Session,
    *,
    name: str,
    resume_text: str,
    min_score: float = 40.0,
    limit: int = 30,
    use_llm: bool = False,
) -> dict:
    """Create profile, embed resume, and rank jobs for this person."""
    display_name = (name or "").strip() or guess_name_from_resume(resume_text)
    profile = Profile(
        name=display_name,
        resume_text=resume_text,
        preferences_json="{}",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    embed_summary = embed_profile(db, profile.id, force=True)
    match_summary = match_profile_to_jobs(
        db,
        profile.id,
        min_score=min_score,
        limit=limit,
        mode="auto",
        use_llm=use_llm,
        store=True,
    )
    logger.info(
        "Onboarded profile %s (%s): %d chunks, %d matches",
        profile.id,
        profile.name,
        embed_summary.get("chunks", 0),
        match_summary.get("matched", 0),
    )
    return {
        "profile_id": profile.id,
        "name": profile.name,
        "chunks": embed_summary.get("chunks", 0),
        "matched": match_summary.get("matched", 0),
        "matches": match_summary.get("matches", []),
    }

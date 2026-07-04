"""Extract resume text and run the match pipeline for a new profile."""

from __future__ import annotations

import io
import logging
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from api.services.rag_pipeline import embed_profile, match_profile_to_jobs
from src.db.models import Profile

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def _extension(filename: str) -> str:
    name = (filename or "").lower().strip()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def extract_resume_text(filename: str, data: bytes) -> str:
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Upload a PDF, DOCX, TXT, or MD resume.")

    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="ignore").strip()

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError("Could not read text from that PDF. Try a text-based PDF.")
        return text

    if ext == ".docx":
        from docx import Document

        document = Document(io.BytesIO(data))
        text = "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()
        if not text:
            raise ValueError("Could not read text from that DOCX file.")
        return text

    raise ValueError("Unsupported file type.")


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or "resume.pdf"
    data = await file.read()
    if not data:
        raise ValueError("Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 5 MB).")
    return filename, data


def create_profile_from_resume(
    db: Session,
    *,
    name: str,
    resume_text: str,
    user_id: Optional[int] = None,
) -> Profile:
    profile = Profile(
        name=name.strip() or "Candidate",
        resume_text=resume_text,
        preferences_json="{}",
        user_id=user_id,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def run_match_pipeline(
    db: Session,
    profile_id: int,
    *,
    min_score: float = 60.0,
    limit: int = 30,
    use_llm: bool = False,
) -> dict:
    """Embed resume and rank jobs. Vector-only by default (fast, no OpenAI cost)."""
    embed_profile(db, profile_id, force=True)
    return match_profile_to_jobs(
        db,
        profile_id,
        min_score=min_score,
        limit=limit,
        mode="auto",
        use_llm=use_llm,
        store=True,
    )

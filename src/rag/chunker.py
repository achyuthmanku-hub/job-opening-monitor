"""Split resumes and job descriptions into chunks for embedding."""

import re

MIN_CHUNK_CHARS = 40
MAX_CHUNK_CHARS = 600


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [part.strip() for part in parts if part.strip()]


def chunk_resume(resume_text: str) -> list[str]:
    paragraphs = _split_paragraphs(resume_text)
    chunks: list[str] = []
    buffer = ""

    for para in paragraphs:
        if len(para) > MAX_CHUNK_CHARS:
            if buffer:
                chunks.append(buffer.strip())
                buffer = ""
            for index in range(0, len(para), MAX_CHUNK_CHARS):
                piece = para[index : index + MAX_CHUNK_CHARS].strip()
                if len(piece) >= MIN_CHUNK_CHARS:
                    chunks.append(piece)
            continue

        candidate = f"{buffer}\n{para}".strip() if buffer else para
        if len(candidate) <= MAX_CHUNK_CHARS:
            buffer = candidate
        else:
            if len(buffer) >= MIN_CHUNK_CHARS:
                chunks.append(buffer.strip())
            buffer = para

    if buffer and len(buffer) >= MIN_CHUNK_CHARS:
        chunks.append(buffer.strip())

    if not chunks and resume_text.strip():
        chunks.append(resume_text.strip()[:MAX_CHUNK_CHARS])

    return chunks


def chunk_job(title: str, description: str = "", location: str = "") -> list[str]:
    header = f"{title}\n{location}".strip()
    chunks: list[str] = []
    if header:
        chunks.append(header[:MAX_CHUNK_CHARS])

    for para in _split_paragraphs(description):
        if len(para) < MIN_CHUNK_CHARS:
            continue
        for index in range(0, len(para), MAX_CHUNK_CHARS):
            piece = para[index : index + MAX_CHUNK_CHARS].strip()
            if len(piece) >= MIN_CHUNK_CHARS:
                chunks.append(piece)

    if not chunks:
        fallback = f"{title}\n{description}".strip()
        if fallback:
            chunks.append(fallback[:MAX_CHUNK_CHARS])

    return chunks

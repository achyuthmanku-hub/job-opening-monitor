import json
import logging
import os
import re

from openai import APIError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "with", "will", "you", "your",
    "our", "we", "this", "have", "has", "job", "role", "team", "work", "using",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z][a-z0-9+#.]{1,}", text.lower())
        if token not in STOP_WORDS and len(token) > 2
    }


def score_resume_match_local(
    resume_text: str,
    job_title: str,
    job_description: str,
) -> tuple[float, str]:
    jd_text = f"{job_title}\n{job_description}"
    jd_tokens = _tokens(jd_text)
    resume_tokens = _tokens(resume_text)

    if not jd_tokens:
        return 70.0, "Local keyword match (limited job description)."

    overlap = jd_tokens & resume_tokens
    keyword_score = (len(overlap) / len(jd_tokens)) * 100

    title_tokens = _tokens(job_title)
    title_overlap = title_tokens & resume_tokens
    title_score = (len(title_overlap) / max(len(title_tokens), 1)) * 100

    score = min(100.0, keyword_score * 0.75 + title_score * 0.25)
    return round(score, 1), f"Local keyword match ({len(overlap)} shared terms)."


def _openai_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "insufficient_quota" in message or "exceeded your current quota" in message


def score_resume_match(
    resume_text: str,
    job_title: str,
    job_description: str,
    *,
    min_score: float = 85.0,
    mode: str = "auto",
) -> tuple[float, str]:
    if mode == "local":
        return score_resume_match_local(resume_text, job_title, job_description)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if mode == "openai" and not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when match_mode is openai.")

    if not api_key:
        logger.warning("OPENAI_API_KEY missing; using local keyword match scoring.")
        return score_resume_match_local(resume_text, job_title, job_description)

    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""
You are an ATS resume matcher. Score how well this resume matches the job on a 0-100 scale.
Focus on skills, experience, seniority, and role fit. Be strict but fair.

Return ONLY valid JSON:
{{"score": <number>, "summary": "<one sentence>"}}

Target threshold: {min_score}

JOB TITLE:
{job_title}

JOB DESCRIPTION:
{job_description[:8000]}

RESUME:
{resume_text[:8000]}
""".strip()

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or ""
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            if mode == "auto":
                return score_resume_match_local(resume_text, job_title, job_description)
            return 0.0, "Could not parse match score."
        payload = json.loads(match.group(0))
        score = float(payload.get("score", 0))
        summary = str(payload.get("summary", "")).strip()
        return score, summary
    except (RateLimitError, APIError) as exc:
        if mode == "openai" or not _openai_quota_error(exc):
            raise
        logger.warning(
            "OpenAI quota/rate limit hit; falling back to local keyword match scoring."
        )
        return score_resume_match_local(resume_text, job_title, job_description)
    except Exception:
        if mode == "auto":
            logger.warning("OpenAI scoring failed; falling back to local keyword match.")
            return score_resume_match_local(resume_text, job_title, job_description)
        raise

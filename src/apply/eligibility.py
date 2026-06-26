import re

from ..models import JobPosting

CLEARANCE_MARKERS = (
    "security clearance",
    "secret clearance",
    "top secret",
    "ts/sci",
    "ts sci",
    "active clearance",
    "clearance required",
    "must have clearance",
    "public trust clearance",
    "dod clearance",
    "government clearance",
)

NO_SPONSORSHIP_MARKERS = (
    "no sponsorship",
    "not provide sponsorship",
    "unable to sponsor",
    "will not sponsor",
    "cannot sponsor",
    "not eligible for sponsorship",
)

SPONSORSHIP_REQUIRED_MARKERS = (
    "visa sponsorship required",
    "requires visa sponsorship",
    "must require sponsorship",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def requires_clearance(text: str) -> bool:
    lower = _normalize(text)
    return any(marker in lower for marker in CLEARANCE_MARKERS)


def job_requires_sponsorship(text: str) -> bool:
    """True when the posting explicitly requires employer visa sponsorship."""
    lower = _normalize(text)
    return any(marker in lower for marker in SPONSORSHIP_REQUIRED_MARKERS)


def job_denies_sponsorship(text: str) -> bool:
    """True when the posting says they will not sponsor visas."""
    lower = _normalize(text)
    return any(marker in lower for marker in NO_SPONSORSHIP_MARKERS)


def is_eligible_for_apply(
    title: str,
    description: str,
    *,
    needs_sponsorship: bool = False,
) -> tuple[bool, str]:
    combined = f"{title}\n{description}"

    if requires_clearance(combined):
        return False, "security_clearance_required"

    if needs_sponsorship:
        if job_denies_sponsorship(combined):
            return False, "no_sponsorship_offered"
        return True, ""

    # Candidate does not need sponsorship — "no sponsorship" postings are fine.
    if job_requires_sponsorship(combined):
        return False, "sponsorship_required"

    return True, ""

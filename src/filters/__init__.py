import re
from datetime import datetime, timezone
from typing import Optional

from ..models import JobPosting

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

NON_US_MARKERS = (
    "united kingdom",
    "uk,",
    ", uk",
    "canada",
    ", ca, canada",
    "india",
    "germany",
    "ireland",
    "singapore",
    "australia",
    "japan",
    "china",
    "mexico",
    "brazil",
    "france",
    "spain",
    "italy",
    "netherlands",
    "poland",
    "israel",
    "korea",
    "taiwan",
    "hong kong",
    "emea",
    "apac",
    "latam",
    "europe",
)


def matches_role(job: JobPosting, keywords: list[str]) -> bool:
    if not keywords:
        return True
    title = job.title.lower()
    return any(keyword in title for keyword in keywords)


def is_us_location(job: JobPosting) -> bool:
    # Some career portals (e.g. Expedia) put location in the title, not location field.
    location = f"{job.location or ''} {job.title or ''}".strip()
    if not location:
        return False

    lower = location.lower()
    if any(marker in lower for marker in NON_US_MARKERS):
        return False

    if any(
        token in lower
        for token in ("united states", "usa", "u.s.a", "u.s.", "america")
    ):
        return True

    if re.search(r"\bremote\b.*\bus\b", lower) or re.search(r"\bus\b.*\bremote\b", lower):
        return True

    state_match = re.search(r",\s*([A-Z]{2})(?:\s|,|$)", location)
    if state_match and state_match.group(1) in US_STATE_CODES:
        return True

    if re.search(r"\bUS\b", location):
        return True

    return False


def _hours_since_posted(posted_at: str, now: datetime) -> Optional[float]:
    if not posted_at or not str(posted_at).strip():
        return None

    text = str(posted_at).strip()

    if text.isdigit():
        timestamp = int(text)
        if timestamp > 1_000_000_000_000:
            timestamp /= 1000
        posted = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return (now - posted).total_seconds() / 3600

    try:
        posted = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return (now - posted.astimezone(timezone.utc)).total_seconds() / 3600
    except ValueError:
        pass

    lower = text.lower()

    hour_match = re.search(r"(\d+)\s*hours?\s*ago", lower)
    if hour_match:
        return float(hour_match.group(1))

    minute_match = re.search(r"(\d+)\s*minutes?\s*ago", lower)
    if minute_match:
        return float(minute_match.group(1)) / 60

    day_match = re.search(r"(\d+)\s*days?\s*ago", lower)
    if day_match:
        return float(day_match.group(1)) * 24

    if "30+" in lower and "day" in lower:
        return 30 * 24

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None

    if "today" in lower:
        return None

    if "yesterday" in lower:
        return 24

    return None


def matches_posted_window(
    job: JobPosting,
    min_hours: float,
    max_hours: float,
    now: Optional[datetime] = None,
    *,
    allow_missing_posted_time: bool = False,
) -> bool:
    now = now or datetime.now(timezone.utc)
    hours = _hours_since_posted(job.posted_at, now)
    if hours is None:
        return allow_missing_posted_time
    return min_hours <= hours <= max_hours


SENIOR_TITLE_PATTERN = re.compile(
    r"\b("
    r"senior|sr\.?|staff|principal|architect|distinguished|director|"
    r"manager|management|head of|vp|vice president|"
    r"lead engineer|tech lead|team lead|engineering lead|"
    r"software engineer iii|software engineer iv|engineer iii|engineer iv|"
    r"sde iii|sde iv|level 5|level 6|level 7|l5|l6|l7|l8"
    r")\b",
    re.IGNORECASE,
)

ENTRY_TITLE_PATTERN = re.compile(
    r"\b("
    r"junior|jr\.?|entry[- ]level|associate|intern|new grad|new graduate|"
    r"early career|graduate|software engineer i\b|engineer i\b|sde i\b|"
    r"software developer i\b|level 1|level 2|l3|l4"
    r")\b",
    re.IGNORECASE,
)

MIN_YEARS_PATTERNS = (
    re.compile(r"(?:minimum|min\.?|at least|required)\s*(?:of\s*)?(\d+)\+?\s*years?", re.I),
    re.compile(r"(\d+)\+\s*years?", re.I),
    re.compile(r"(\d+)\+\s*years?(?:\s+of)?\s+(?:experience|exp)", re.I),
    re.compile(r"(\d+)\s*[-–to]+\s*(\d+)\+?\s*years?", re.I),
    re.compile(r"(\d+)\s*years?\s+(?:of\s+)?(?:experience|exp)", re.I),
)


def _experience_text(job: JobPosting, extra_text: str = "") -> str:
    return f"{job.title or ''}\n{job.location or ''}\n{extra_text}".strip()


def _minimum_years_required(text: str) -> Optional[int]:
    lower = text.lower()
    minimums: list[int] = []

    for pattern in MIN_YEARS_PATTERNS:
        for match in pattern.finditer(lower):
            groups = [g for g in match.groups() if g is not None]
            if not groups:
                continue
            minimums.append(int(groups[0]))

    return max(minimums) if minimums else None


def matches_experience(
    job: JobPosting,
    *,
    min_years: int = 0,
    max_years: int = 5,
    extra_text: str = "",
) -> bool:
    """Keep roles targeting roughly 0-5 years experience; skip senior/high-min roles."""
    text = _experience_text(job, extra_text)
    title = job.title or ""

    if ENTRY_TITLE_PATTERN.search(title):
        return True

    if SENIOR_TITLE_PATTERN.search(title):
        return False

    required_min = _minimum_years_required(text)
    if required_min is not None:
        if required_min < min_years:
            return False
        if required_min > max_years:
            return False

    return True


def job_matches_filters(job: JobPosting, settings: dict, now: Optional[datetime] = None) -> bool:
    if settings.get("us_only", True) and not is_us_location(job):
        return False
    if not matches_role(job, settings.get("keywords", [])):
        return False
    if settings.get("experience_filter_enabled", True) and not matches_experience(
        job,
        min_years=int(settings.get("experience_min_years", 0)),
        max_years=int(settings.get("experience_max_years", 5)),
    ):
        return False
    return matches_posted_window(
        job,
        settings.get("posted_min_hours", 1),
        settings.get("posted_max_hours", 5),
        now=now,
        allow_missing_posted_time=settings.get("allow_missing_posted_time", False),
    )

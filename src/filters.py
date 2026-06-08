import re
from datetime import datetime, timezone
from typing import Optional

from .models import JobPosting

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


def job_matches_filters(job: JobPosting, settings: dict, now: Optional[datetime] = None) -> bool:
    if settings.get("us_only", True) and not is_us_location(job):
        return False
    if not matches_role(job, settings.get("keywords", [])):
        return False
    return matches_posted_window(
        job,
        settings.get("posted_min_hours", 1),
        settings.get("posted_max_hours", 5),
        now=now,
        allow_missing_posted_time=settings.get("allow_missing_posted_time", False),
    )

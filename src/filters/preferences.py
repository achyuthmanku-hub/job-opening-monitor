"""Preference-aware job filtering."""

from __future__ import annotations

from typing import Optional

from src.filters import job_matches_filters
from src.models import JobPosting


COUNTRY_MARKERS: dict[str, tuple[str, ...]] = {
    "US": (
        "united states",
        "usa",
        "u.s.a",
        "u.s.",
        "america",
    ),
    "CA": ("canada", ", ca", "ontario", "british columbia", "quebec"),
    "UK": ("united kingdom", ", uk", "england", "scotland", "london"),
    "DE": ("germany", "berlin", "munich"),
    "IN": ("india", "bangalore", "bengaluru", "hyderabad", "mumbai"),
}


def _location_text(job: JobPosting) -> str:
    return f"{job.location or ''} {job.title or ''}".lower()


def matches_countries(job: JobPosting, countries: list[str]) -> bool:
    if not countries:
        return True
    text = _location_text(job)
    if any(token in text for token in ("remote", "anywhere", "global")):
        return True
    for code in countries:
        markers = COUNTRY_MARKERS.get(code.upper(), ())
        if any(marker in text for marker in markers):
            return True
        if code.upper() == "US":
            from src.filters import is_us_location

            if is_us_location(job):
                return True
    return False


def matches_work_authorization(
    *,
    sponsorship_mentioned: bool,
    requires_clearance: bool,
    preference: str,
    skip_clearance: bool,
) -> bool:
    if skip_clearance and requires_clearance:
        return False
    if preference == "any":
        return True
    if preference == "no_sponsorship_needed" and sponsorship_mentioned:
        return False
    return True


def job_matches_preferences(
    job: JobPosting,
    settings: dict,
    preferences: dict,
    *,
    sponsorship_mentioned: bool = False,
    requires_clearance: bool = False,
) -> bool:
    merged = dict(settings)
    if preferences.get("keywords"):
        merged["keywords"] = [k.lower() for k in preferences["keywords"]]
    countries = preferences.get("countries")
    if countries:
        merged["us_only"] = False

    if not job_matches_filters(job, merged):
        return False

    if countries and not matches_countries(job, countries):
        return False

    return matches_work_authorization(
        sponsorship_mentioned=sponsorship_mentioned,
        requires_clearance=requires_clearance,
        preference=preferences.get("work_authorization", "any"),
        skip_clearance=preferences.get("skip_clearance", True),
    )

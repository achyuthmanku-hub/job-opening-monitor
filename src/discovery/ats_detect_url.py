"""Detect ATS type and scraper config from a careers URL."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

GREENHOUSE_HOSTS = ("boards.greenhouse.io", "job-boards.greenhouse.io")
ASHBY_HOST = "jobs.ashbyhq.com"
LEVER_HOST = "jobs.lever.co"
WORKDAY_SUFFIX = ".myworkdayjobs.com"
ORACLE_SUFFIX = ".oraclecloud.com"
AMAZON_HOSTS = ("amazon.jobs", "www.amazon.jobs")
SMARTRECRUITERS_HOST = "jobs.smartrecruiters.com"

EMBED_PATTERNS = [
    (re.compile(r"boards\.greenhouse\.io/([a-zA-Z0-9_-]+)", re.I), "greenhouse"),
    (re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)", re.I), "ashby"),
    (re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_-]+)", re.I), "lever"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.wd\d+\.myworkdayjobs\.com", re.I), "workday"),
    (re.compile(r"([a-z0-9-]+)\.fa\.oraclecloud\.com", re.I), "oracle"),
]


@dataclass
class AtsDetection:
    ats_type: str
    company_name: str
    source: dict
    careers_url: str
    confidence: str  # high | medium | low

    def to_dict(self) -> dict:
        return {
            "ats_type": self.ats_type,
            "company_name": self.company_name,
            "source": self.source,
            "careers_url": self.careers_url,
            "confidence": self.confidence,
        }


def _guess_company_name(url: str, slug: str = "") -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if slug:
        return slug.replace("-", " ").title()
    base = host.split(".")[0]
    return base.replace("-", " ").title()


def _slug_from_path(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p]
    return parts[0] if parts else ""


def detect_ats(url: str, *, company_name: Optional[str] = None) -> Optional[AtsDetection]:
    """Detect ATS from URL patterns without network calls."""
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        url = f"https://{url.strip()}"
        parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path
    name = company_name or _guess_company_name(url)

    for gh_host in GREENHOUSE_HOSTS:
        if gh_host in host:
            slug = _slug_from_path(path) or name.lower().replace(" ", "")
            return AtsDetection(
                ats_type="greenhouse",
                company_name=name,
                source={"type": "greenhouse", "slug": slug},
                careers_url=url,
                confidence="high",
            )

    if ASHBY_HOST in host:
        slug = _slug_from_path(path)
        if slug:
            return AtsDetection(
                ats_type="ashby",
                company_name=name,
                source={"type": "ashby", "slug": slug},
                careers_url=url,
                confidence="high",
            )

    if LEVER_HOST in host:
        slug = _slug_from_path(path)
        if slug:
            return AtsDetection(
                ats_type="lever",
                company_name=name,
                source={"type": "lever", "slug": slug},
                careers_url=url,
                confidence="high",
            )

    if host.endswith(WORKDAY_SUFFIX) or WORKDAY_SUFFIX[1:] in host:
        # e.g. ghr.wd1.myworkdayjobs.com/lateral-us
        tenant = host.split(".")[0]
        wd = "wd1"
        for part in host.split("."):
            if part.startswith("wd") and part[2:].isdigit():
                wd = part
        site = _slug_from_path(path) or "external"
        return AtsDetection(
            ats_type="workday",
            company_name=name,
            source={"type": "workday", "tenant": tenant, "wd": wd, "site": site},
            careers_url=url,
            confidence="medium",
        )

    if ORACLE_SUFFIX in host:
        site = _slug_from_path(path) or "CX_1001"
        return AtsDetection(
            ats_type="oracle",
            company_name=name,
            source={"type": "oracle", "host": host, "site": site},
            careers_url=url,
            confidence="medium",
        )

    if any(ah in host for ah in AMAZON_HOSTS):
        return AtsDetection(
            ats_type="amazon",
            company_name="Amazon",
            source={"type": "amazon", "query": ""},
            careers_url=url,
            confidence="high",
        )

    if SMARTRECRUITERS_HOST in host:
        slug = _slug_from_path(path)
        if slug:
            return AtsDetection(
                ats_type="smartrecruiters",
                company_name=name,
                source={"type": "smartrecruiters", "slug": slug},
                careers_url=url,
                confidence="high",
            )

    return None


def _probe_greenhouse_slug(slug: str, timeout: int = 10) -> bool:
    api = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        response = requests.get(api, timeout=timeout)
        return response.status_code == 200 and "jobs" in response.json()
    except Exception:
        return False


def probe_careers_url(
    url: str,
    *,
    company_name: Optional[str] = None,
    timeout: int = 15,
    user_agent: str = "JobOpeningMonitor/1.0",
) -> Optional[AtsDetection]:
    """Fetch a careers page and detect embedded ATS links or probe Greenhouse slug."""
    direct = detect_ats(url, company_name=company_name)
    if direct and direct.confidence == "high":
        return direct

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": user_agent},
            allow_redirects=True,
        )
        response.raise_for_status()
        final_url = response.url
        redirected = detect_ats(final_url, company_name=company_name)
        if redirected:
            return redirected

        html = response.text
        for pattern, ats_type in EMBED_PATTERNS:
            match = pattern.search(html)
            if not match:
                continue
            token = match.group(1)
            if ats_type == "greenhouse":
                return AtsDetection(
                    ats_type="greenhouse",
                    company_name=company_name or _guess_company_name(url, token),
                    source={"type": "greenhouse", "slug": token},
                    careers_url=final_url,
                    confidence="medium",
                )
            if ats_type == "ashby":
                return AtsDetection(
                    ats_type="ashby",
                    company_name=company_name or _guess_company_name(url, token),
                    source={"type": "ashby", "slug": token},
                    careers_url=final_url,
                    confidence="medium",
                )
            if ats_type == "lever":
                return AtsDetection(
                    ats_type="lever",
                    company_name=company_name or _guess_company_name(url, token),
                    source={"type": "lever", "slug": token},
                    careers_url=final_url,
                    confidence="medium",
                )

        # Guess Greenhouse slug from domain (stripe.com -> stripe)
        host = urlparse(final_url).netloc.lower().removeprefix("www.")
        slug_guess = host.split(".")[0]
        if slug_guess and _probe_greenhouse_slug(slug_guess, timeout=timeout):
            return AtsDetection(
                ats_type="greenhouse",
                company_name=company_name or _guess_company_name(url, slug_guess),
                source={"type": "greenhouse", "slug": slug_guess},
                careers_url=final_url,
                confidence="low",
            )
    except Exception:
        logger.debug("Probe failed for %s", url, exc_info=True)

    if direct:
        return direct

    name = company_name or _guess_company_name(url)
    return AtsDetection(
        ats_type="career_portal",
        company_name=name,
        source={"type": "career_portal", "url": url},
        careers_url=url,
        confidence="low",
    )

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import fetch_html

JOB_VIEW_PATTERN = re.compile(r"linkedin\.com/jobs/view/", re.IGNORECASE)
NOISE_TITLES = {
    "jobs",
    "join now",
    "sign in",
    "follow",
    "see jobs",
    "see all jobs",
    "report this company",
    "about",
    "accessibility",
    "privacy policy",
    "cookie policy",
    "user agreement",
    "copyright policy",
    "brand policy",
    "guest controls",
    "community guidelines",
}


def fetch_linkedin(company: str, source: dict, settings: dict) -> list[JobPosting]:
    """
    LinkedIn aggressively blocks bots. This scraper works best when you provide
    the public company jobs URL. For reliability, prefer Greenhouse/Lever/Ashby
    or the company's own careers page as primary sources.
    """
    url = source["url"]
    html = fetch_html(url, settings)
    soup = BeautifulSoup(html, "lxml")
    seen_urls: set[str] = set()
    jobs: list[JobPosting] = []

    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href or not JOB_VIEW_PATTERN.search(href):
            continue

        if href.startswith("/"):
            href = urljoin("https://www.linkedin.com", href)

        if href in seen_urls:
            continue

        title = anchor.get_text(" ", strip=True)
        if not title or len(title) < 8:
            continue
        if title.lower() in NOISE_TITLES:
            continue
        if title.lower().endswith(" open jobs"):
            continue
        if title.lower() == company.lower():
            continue

        seen_urls.add(href)
        jobs.append(
            JobPosting(
                company=company,
                title=title[:200],
                url=href.split("?")[0],
                source=f"linkedin:{url}",
            )
        )

    return jobs

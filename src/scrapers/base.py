import re
from typing import Optional

from bs4 import BeautifulSoup

from ..models import JobPosting
from .rate_limit import http_get

JOB_LINK_PATTERNS = re.compile(
    r"(job|career|position|opening|role|apply|posting|vacanc)",
    re.IGNORECASE,
)


def fetch_html(url: str, settings: dict) -> str:
    response = http_get(url, settings)
    return response.text


def extract_links_from_html(
    html: str,
    base_url: str,
    company: str,
    source: str,
    *,
    link_selector: str = "a[href]",
    title_attr: Optional[str] = None,
) -> list[JobPosting]:
    soup = BeautifulSoup(html, "lxml")
    seen_urls: set[str] = set()
    jobs: list[JobPosting] = []

    for anchor in soup.select(link_selector):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue

        if href.startswith("/"):
            from urllib.parse import urljoin

            href = urljoin(base_url, href)

        if href in seen_urls:
            continue

        title = ""
        if title_attr and anchor.get(title_attr):
            title = anchor[title_attr].strip()
        else:
            title = anchor.get_text(" ", strip=True)

        if not title or len(title) < 4:
            continue

        if not JOB_LINK_PATTERNS.search(href) and not JOB_LINK_PATTERNS.search(title):
            continue

        seen_urls.add(href)
        jobs.append(
            JobPosting(
                company=company,
                title=title[:200],
                url=href,
                source=source,
            )
        )

    return jobs

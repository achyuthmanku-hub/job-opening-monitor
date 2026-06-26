import re
from html import unescape
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ..models import JobPosting


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return unescape(re.sub(r"\n{3,}", "\n\n", text))


def _fetch_greenhouse_description(url: str, settings: dict) -> str:
    match = re.search(r"greenhouse\.io/[^/]+/jobs/(\d+)", url, re.I)
    if not match:
        return ""
    job_id = match.group(1)
    board_match = re.search(r"boards\.greenhouse\.io/([^/]+)/", url, re.I)
    if not board_match:
        return ""
    slug = board_match.group(1)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
    response = requests.get(
        api_url,
        timeout=settings["request_timeout"],
        headers={"User-Agent": settings["user_agent"]},
    )
    response.raise_for_status()
    payload = response.json()
    content = payload.get("content", "")
    if content:
        return _strip_html(content)
    return payload.get("title", "")


def _fetch_ashby_description(url: str, settings: dict) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return ""
    org, job_id = parts[0], parts[-1]
    api_url = "https://jobs.ashbyhq.com/api/non-user-graphql"
    query = """
    query JobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
      jobPosting(
        organizationHostedJobsPageName: $organizationHostedJobsPageName
        jobPostingId: $jobPostingId
      ) {
        title
        descriptionHtml
      }
    }
    """
    response = requests.post(
        api_url,
        json={
            "operationName": "JobPosting",
            "variables": {
                "organizationHostedJobsPageName": org,
                "jobPostingId": job_id,
            },
            "query": query,
        },
        timeout=settings["request_timeout"],
        headers={
            "User-Agent": settings["user_agent"],
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    posting = payload.get("data", {}).get("jobPosting") or {}
    html = posting.get("descriptionHtml", "")
    return _strip_html(html) if html else posting.get("title", "")


def _fetch_html_description(url: str, settings: dict) -> str:
    response = requests.get(
        url,
        timeout=settings["request_timeout"],
        headers={"User-Agent": settings["user_agent"]},
    )
    response.raise_for_status()
    return _strip_html(response.text)


def fetch_job_description(job: JobPosting, settings: dict) -> str:
    url = job.url.lower()
    try:
        if "greenhouse.io" in url:
            text = _fetch_greenhouse_description(job.url, settings)
            if text:
                return text[:12000]
        if "ashbyhq.com" in url:
            text = _fetch_ashby_description(job.url, settings)
            if text:
                return text[:12000]
        text = _fetch_html_description(job.url, settings)
        return text[:12000]
    except Exception:
        return f"{job.title}\n{job.location}".strip()

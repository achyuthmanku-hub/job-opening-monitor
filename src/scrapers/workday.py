from ..models import JobPosting
from .rate_limit import http_post


def _search_query(settings: dict) -> str:
    keywords = settings.get("keywords", [])
    return keywords[0] if keywords else ""


def fetch_workday(company: str, source: dict, settings: dict) -> list[JobPosting]:
    tenant = source["tenant"]
    wd = source.get("wd", "wd1")
    site = source["site"]
    max_jobs = source.get("max_jobs", 300)
    search_text = source.get("query") or _search_query(settings)
    host = f"https://{tenant}.{wd}.myworkdayjobs.com"
    url = f"{host}/wday/cxs/{tenant}/{site}/jobs"

    jobs: list[JobPosting] = []
    offset = 0
    limit = 20

    while len(jobs) < max_jobs:
        response = http_post(
            url,
            settings,
            json={
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": search_text,
            },
            headers={"Content-Type": "application/json"},
        )
        payload = response.json()
        postings = payload.get("jobPostings", [])
        if not postings:
            break

        for item in postings:
            external_path = item.get("externalPath", "")
            job_url = f"{host}{external_path}" if external_path else host
            jobs.append(
                JobPosting(
                    company=company,
                    title=item.get("title", "Untitled"),
                    url=job_url,
                    source=f"workday:{tenant}/{site}",
                    location=item.get("locationsText", ""),
                    posted_at=item.get("postedOn", ""),
                )
            )

        offset += len(postings)
        total = payload.get("total", 0)
        if offset >= total or len(jobs) >= max_jobs:
            break

    return jobs[:max_jobs]

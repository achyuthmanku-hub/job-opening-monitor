import requests

from ..models import JobPosting


def _search_query(settings: dict) -> str:
    keywords = settings.get("keywords", [])
    return keywords[0] if keywords else ""


def fetch_amazon(company: str, source: dict, settings: dict) -> list[JobPosting]:
    base_query = source.get("query") or _search_query(settings)
    max_jobs = source.get("max_jobs", 200)
    jobs: list[JobPosting] = []
    offset = 0
    page_size = 100

    while len(jobs) < max_jobs:
        response = requests.get(
            "https://www.amazon.jobs/en/search.json",
            params={
                "base_query": base_query,
                "offset": offset,
                "result_limit": page_size,
            },
            timeout=settings["request_timeout"],
            headers={"User-Agent": settings["user_agent"]},
        )
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("jobs", [])
        if not batch:
            break

        for item in batch:
            job_path = item.get("job_path", "")
            jobs.append(
                JobPosting(
                    company=company,
                    title=item.get("title", "Untitled"),
                    url=f"https://www.amazon.jobs{job_path}",
                    source="amazon:jobs",
                    location=item.get("normalized_location", item.get("city", "")),
                    posted_at=item.get("posted_date", ""),
                )
            )

        offset += len(batch)
        if len(batch) < page_size or len(jobs) >= max_jobs:
            break

    return jobs[:max_jobs]

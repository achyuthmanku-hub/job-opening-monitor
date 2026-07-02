from ..models import JobPosting
from .rate_limit import http_get


def fetch_greenhouse(company: str, source: dict, settings: dict) -> list[JobPosting]:
    slug = source["slug"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    response = http_get(url, settings)
    payload = response.json()

    jobs: list[JobPosting] = []
    for item in payload.get("jobs", []):
        jobs.append(
            JobPosting(
                company=company,
                title=item.get("title", "Untitled"),
                url=item.get("absolute_url", ""),
                source=f"greenhouse:{slug}",
                location=item.get("location", {}).get("name", ""),
                posted_at=item.get("first_published", item.get("updated_at", "")),
            )
        )
    return jobs

import requests

from ..models import JobPosting


def fetch_greenhouse(company: str, source: dict, settings: dict) -> list[JobPosting]:
    slug = source["slug"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    response = requests.get(
        url,
        timeout=settings["request_timeout"],
        headers={"User-Agent": settings["user_agent"]},
    )
    response.raise_for_status()
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
                posted_at=item.get("updated_at", ""),
            )
        )
    return jobs

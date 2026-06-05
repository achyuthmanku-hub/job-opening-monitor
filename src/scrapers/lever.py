import requests

from ..models import JobPosting


def fetch_lever(company: str, source: dict, settings: dict) -> list[JobPosting]:
    slug = source["slug"]
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    response = requests.get(
        url,
        timeout=settings["request_timeout"],
        headers={"User-Agent": settings["user_agent"]},
    )
    response.raise_for_status()
    postings = response.json()

    jobs: list[JobPosting] = []
    for item in postings:
        jobs.append(
            JobPosting(
                company=company,
                title=item.get("text", "Untitled"),
                url=item.get("hostedUrl", item.get("applyUrl", "")),
                source=f"lever:{slug}",
                location=item.get("categories", {}).get("location", ""),
                posted_at=str(item.get("createdAt", "")),
            )
        )
    return jobs

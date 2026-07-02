from ..models import JobPosting
from .rate_limit import http_get


def fetch_smartrecruiters(company: str, source: dict, settings: dict) -> list[JobPosting]:
    slug = source["slug"]
    jobs: list[JobPosting] = []
    offset = 0
    limit = 100

    while True:
        response = http_get(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
            settings,
            params={"offset": offset, "limit": limit},
        )
        payload = response.json()
        batch = payload.get("content", [])
        if not batch:
            break

        for item in batch:
            posting_id = item.get("id", "")
            jobs.append(
                JobPosting(
                    company=company,
                    title=item.get("name", "Untitled"),
                    url=item.get("ref", "")
                    or f"https://jobs.smartrecruiters.com/{slug}/{posting_id}",
                    source=f"smartrecruiters:{slug}",
                    location=item.get("location", {}).get("city", ""),
                    posted_at=item.get("releasedDate", ""),
                )
            )

        offset += len(batch)
        total = payload.get("totalFound", 0)
        if offset >= total:
            break

    return jobs

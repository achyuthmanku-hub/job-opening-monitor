from ..models import JobPosting
from .rate_limit import http_get


def _search_query(settings: dict) -> str:
    keywords = settings.get("keywords", [])
    return keywords[0] if keywords else ""


def fetch_oracle(company: str, source: dict, settings: dict) -> list[JobPosting]:
    host = source["host"]
    site = source["site"]
    max_jobs = source.get("max_jobs", 300)
    keyword = source.get("query") or _search_query(settings)
    base_url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}"
    api_url = (
        f"https://{host}/hcmRestApi/resources/latest/"
        f"recruitingCEJobRequisitions?expand=all&onlyData=true"
    )

    jobs: list[JobPosting] = []
    offset = 0
    limit = 25

    while len(jobs) < max_jobs:
        finder = (
            f"findReqs;siteNumber={site},keyword={keyword},limit={limit},"
            f"offset={offset},sortBy=POSTING_DATES_DESC"
        )
        response = http_get(
            api_url,
            settings,
            params={"finder": finder},
        )
        items = response.json().get("items", [])
        if not items:
            break

        result = items[0]
        requisitions = result.get("requisitionList", [])
        if not requisitions:
            break

        for item in requisitions:
            req_id = item.get("Id", "")
            jobs.append(
                JobPosting(
                    company=company,
                    title=item.get("Title", "Untitled"),
                    url=f"{base_url}/job/{req_id}",
                    source=f"oracle:{host}/{site}",
                    location=item.get("PrimaryLocation", ""),
                    posted_at=item.get("PostedDate", ""),
                )
            )

        offset += len(requisitions)
        total = result.get("TotalJobsCount", 0)
        if offset >= total or len(jobs) >= max_jobs:
            break

    return jobs[:max_jobs]

from ..models import JobPosting
from .rate_limit import http_post


def fetch_ashby(company: str, source: dict, settings: dict) -> list[JobPosting]:
    slug = source["slug"]
    url = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    payload = {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": slug},
        "query": """
        query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
          jobBoard: jobBoardWithTeams(
            organizationHostedJobsPageName: $organizationHostedJobsPageName
          ) {
            jobPostings {
              id
              title
              locationName
            }
          }
        }
        """,
    }
    response = http_post(
        url,
        settings,
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    data = response.json()
    postings = (
        data.get("data", {}).get("jobBoard", {}).get("jobPostings", []) or []
    )

    jobs: list[JobPosting] = []
    for item in postings:
        job_id = item.get("id", "")
        jobs.append(
            JobPosting(
                company=company,
                title=item.get("title", "Untitled"),
                url=f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                source=f"ashby:{slug}",
                location=item.get("locationName", ""),
            )
        )
    return jobs

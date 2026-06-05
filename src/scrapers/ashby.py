import requests

from ..models import JobPosting


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
    response = requests.post(
        url,
        json=payload,
        timeout=settings["request_timeout"],
        headers={
            "User-Agent": settings["user_agent"],
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
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

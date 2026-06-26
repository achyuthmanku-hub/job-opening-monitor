from typing import Optional

from ..models import JobPosting


def detect_ats(job: JobPosting) -> Optional[str]:
    url = job.url.lower()
    source = job.source.lower()

    if "greenhouse.io" in url or "greenhouse" in source:
        return "greenhouse"
    if "ashbyhq.com" in url or "ashby" in source:
        return "ashby"
    if "lever.co" in url or "lever" in source:
        return "lever"
    if "amazon.jobs" in url or "amazon:jobs" in source:
        return "amazon"
    if "oraclecloud.com" in url or source.startswith("oracle:"):
        return "oracle"
    if "myworkdayjobs.com" in url or "workday" in source:
        return "workday"
    return None

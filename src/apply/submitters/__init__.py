from pathlib import Path
from typing import Optional

from ...models import JobPosting
from ..profile import ApplicationProfile
from .amazon import submit_amazon
from .ashby import submit_ashby
from .base import ApplyBrowserSession, run_with_browser
from .common import SubmitResult
from .greenhouse import submit_greenhouse
from .lever import submit_lever
from .oracle import submit_oracle
from .workday import submit_workday

_SUBMITTERS = {
    "greenhouse": submit_greenhouse,
    "ashby": submit_ashby,
    "workday": submit_workday,
    "oracle": submit_oracle,
    "amazon": submit_amazon,
    "lever": submit_lever,
}


def submit_application(
    ats: str,
    job: JobPosting,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
    *,
    headless: bool = True,
    browser_session: Optional[ApplyBrowserSession] = None,
    slow_mo: int = 100,
) -> SubmitResult:
    handler = _SUBMITTERS.get(ats)
    if not handler:
        return SubmitResult(success=False, message=f"Unsupported ATS: {ats}", ats=ats)

    return run_with_browser(
        headless,
        handler,
        profile=profile,
        job_url=job.url,
        resume_path=resume_path,
        credentials=credentials,
        ats=ats,
        browser_session=browser_session,
        slow_mo=slow_mo,
    )

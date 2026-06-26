from pathlib import Path

from playwright.sync_api import Page

from ..profile import ApplicationProfile
from .candidate_experience import submit_candidate_experience
from .common import SubmitResult


def submit_oracle(
    page: Page,
    job_url: str,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
) -> SubmitResult:
    return submit_candidate_experience(
        page,
        job_url,
        resume_path,
        profile,
        credentials,
        ats="oracle",
    )

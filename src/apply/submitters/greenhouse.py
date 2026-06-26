from pathlib import Path

from playwright.sync_api import Page

from ..profile import ApplicationProfile
from .common import (
    SubmitResult,
    answer_work_authorization,
    click_first_visible,
    fill_standard_contact,
    save_failure_screenshot,
    upload_resume,
)


def submit_greenhouse(
    page: Page,
    job_url: str,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
) -> SubmitResult:
    email = credentials.get("email") or profile.email
    page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    click_first_visible(
        page,
        [
            "a#apply_button",
            "a:has-text('Apply for this job')",
            "button:has-text('Apply for this job')",
            "a:has-text('Apply')",
            "button:has-text('Apply')",
        ],
    )
    page.wait_for_timeout(1500)

    fill_standard_contact(page, profile, email)
    upload_resume(page, resume_path)
    answer_work_authorization(page, profile.needs_sponsorship)

    submitted = click_first_visible(
        page,
        [
            "input[type='submit'][value*='Submit']",
            "button:has-text('Submit application')",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "#submit_app",
        ],
        timeout_ms=8000,
    )
    page.wait_for_timeout(3000)

    content = page.content().lower()
    if submitted and any(
        token in content
        for token in ("thank you", "application submitted", "received your application")
    ):
        return SubmitResult(success=True, message="Greenhouse application submitted.", ats="greenhouse")

    if submitted:
        return SubmitResult(
            success=True,
            message="Greenhouse submit clicked; verify confirmation email.",
            ats="greenhouse",
        )

    save_failure_screenshot(page, resume_path.parent, "greenhouse_failed")
    return SubmitResult(success=False, message="Could not submit Greenhouse application.", ats="greenhouse")

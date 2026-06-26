from pathlib import Path

from playwright.sync_api import Page

from ..profile import ApplicationProfile
from .common import (
    SubmitResult,
    answer_work_authorization,
    click_first_visible,
    fill_first_visible,
    fill_standard_contact,
    save_failure_screenshot,
    upload_resume,
)


def submit_lever(
    page: Page,
    job_url: str,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
) -> SubmitResult:
    email = credentials.get("email") or profile.email
    apply_url = job_url if job_url.rstrip("/").endswith("/apply") else job_url.rstrip("/") + "/apply"
    page.goto(apply_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    fill_standard_contact(page, profile, email)
    fill_first_visible(page, ["input[name='name']"], profile.full_name)
    fill_first_visible(page, ["input[name='org']"], profile.experience[0]["company"] if profile.experience else "")
    upload_resume(page, resume_path)
    answer_work_authorization(page, profile.needs_sponsorship)

    submitted = click_first_visible(
        page,
        [
            "button:has-text('Submit application')",
            "button.template-btn-submit",
            "button[type='submit']",
        ],
        timeout_ms=8000,
    )
    page.wait_for_timeout(3000)

    content = page.content().lower()
    if submitted and "thank" in content:
        return SubmitResult(success=True, message="Lever application submitted.", ats="lever")
    if submitted:
        return SubmitResult(success=True, message="Lever submit clicked.", ats="lever")

    save_failure_screenshot(page, resume_path.parent, "lever_failed")
    return SubmitResult(success=False, message="Could not submit Lever application.", ats="lever")

from pathlib import Path

from playwright.sync_api import Page

from ..profile import ApplicationProfile
from .common import (
    SubmitResult,
    answer_work_authorization,
    click_first_visible,
    detect_submission_blocked,
    fill_standard_contact,
    human_pause,
    save_failure_screenshot,
    upload_resume,
)


def submit_ashby(
    page: Page,
    job_url: str,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
) -> SubmitResult:
    email = credentials.get("email") or profile.email
    try:
        page.goto(job_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2500)

        click_first_visible(
            page,
            [
                "button:has-text('Apply for this role')",
                "button:has-text('Apply for this job')",
                "button:has-text('Apply')",
                "a:has-text('Apply for this role')",
                "a:has-text('Apply')",
            ],
            timeout_ms=10000,
        )
        page.wait_for_timeout(2500)

        for step in range(6):
            fill_standard_contact(page, profile, email)
            human_pause(page, 600, 1400)
            upload_resume(page, resume_path)
            human_pause(page, 800, 1600)
            answer_work_authorization(page, profile.needs_sponsorship)
            human_pause(page, 500, 1000)

            submitted = click_first_visible(
                page,
                [
                    "button:has-text('Submit application')",
                    "button:has-text('Submit Application')",
                    "button:has-text('Submit')",
                ],
                timeout_ms=3000,
            )
            if submitted:
                page.wait_for_timeout(6000)
                blocked = detect_submission_blocked(page)
                if blocked:
                    save_failure_screenshot(page, resume_path.parent, "ashby_blocked")
                    return SubmitResult(
                        success=False,
                        message=f"Ashby blocked submission: {blocked}",
                        ats="ashby",
                        blocked=True,
                    )
                break

            advanced = click_first_visible(
                page,
                [
                    "button:has-text('Continue')",
                    "button:has-text('Next')",
                    "button:has-text('Review')",
                ],
                timeout_ms=4000,
            )
            if not advanced:
                break
            human_pause(page, 1500, 3000)

        blocked = detect_submission_blocked(page)
        if blocked:
            save_failure_screenshot(page, resume_path.parent, "ashby_blocked")
            return SubmitResult(
                success=False,
                message=f"Ashby blocked submission: {blocked}",
                ats="ashby",
                blocked=True,
            )

        content = page.content().lower()
        if any(
            token in content
            for token in (
                "thank you",
                "application submitted",
                "received your application",
                "we received",
            )
        ):
            return SubmitResult(success=True, message="Ashby application submitted.", ats="ashby")

        save_failure_screenshot(page, resume_path.parent, "ashby_failed")
        return SubmitResult(
            success=False,
            message="Ashby submit not confirmed — check ashby_failed.png in application folder.",
            ats="ashby",
        )
    except Exception as exc:
        save_failure_screenshot(page, resume_path.parent, "ashby_error")
        return SubmitResult(success=False, message=str(exc), ats="ashby")

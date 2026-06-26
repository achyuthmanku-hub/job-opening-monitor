from pathlib import Path

from playwright.sync_api import Page

from ..profile import ApplicationProfile
from .common import (
    SubmitResult,
    answer_work_authorization,
    click_first_visible,
    detect_submission_blocked,
    human_pause,
    human_type,
    save_failure_screenshot,
    upload_resume,
)

SUCCESS_MARKERS = (
    "thank you",
    "application submitted",
    "successfully submitted",
    "we received your application",
)


def submit_amazon(
    page: Page,
    job_url: str,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
) -> SubmitResult:
    email = credentials.get("email") or profile.email
    password = credentials.get("password", "")

    try:
        page.goto(job_url, wait_until="domcontentloaded", timeout=90000)
        human_pause(page, 2000, 3500)

        click_first_visible(
            page,
            [
                "a#apply-button",
                "button#apply-button",
                "a:has-text('Apply for this job')",
                "button:has-text('Apply for this job')",
                "a:has-text('Apply')",
                "button:has-text('Apply')",
            ],
            timeout_ms=10000,
        )
        human_pause(page, 2000, 3500)

        _amazon_sign_in(page, email, password, profile)

        for _ in range(12):
            human_type(page, ["input[name='firstName']", "#firstName"], profile.first_name)
            human_type(page, ["input[name='lastName']", "#lastName"], profile.last_name)
            human_type(page, ["input[type='email']", "input[name='email']"], email)
            human_type(page, ["input[type='tel']", "input[name='phone']"], profile.phone)
            if profile.linkedin_url:
                human_type(
                    page,
                    ["input[name*='linkedin']", "input[placeholder*='LinkedIn']"],
                    profile.linkedin_url,
                )

            upload_resume(page, resume_path)
            answer_work_authorization(page, profile.needs_sponsorship)
            human_pause(page, 600, 1200)

            blocked = detect_submission_blocked(page)
            if blocked:
                save_failure_screenshot(page, resume_path.parent, "amazon_blocked")
                return SubmitResult(
                    success=False,
                    message=f"Amazon blocked submission: {blocked}",
                    ats="amazon",
                    blocked=True,
                )

            if click_first_visible(
                page,
                [
                    "button:has-text('Submit application')",
                    "button:has-text('Submit Application')",
                    "button:has-text('Submit')",
                    "input[type='submit']",
                ],
                timeout_ms=3000,
            ):
                human_pause(page, 5000, 7000)
                content = page.content().lower()
                if any(m in content for m in SUCCESS_MARKERS):
                    return SubmitResult(
                        success=True,
                        message="Amazon application submitted.",
                        ats="amazon",
                    )

            if click_first_visible(
                page,
                [
                    "button:has-text('Continue')",
                    "button:has-text('Next')",
                    "button:has-text('Save and continue')",
                ],
                timeout_ms=3000,
            ):
                human_pause(page, 2000, 3500)
                continue

            content = page.content().lower()
            if any(m in content for m in SUCCESS_MARKERS):
                return SubmitResult(
                    success=True,
                    message="Amazon application submitted.",
                    ats="amazon",
                )
            break

        save_failure_screenshot(page, resume_path.parent, "amazon_failed")
        return SubmitResult(
            success=False,
            message="Amazon application flow did not complete.",
            ats="amazon",
        )
    except Exception as exc:
        save_failure_screenshot(page, resume_path.parent, "amazon_error")
        return SubmitResult(success=False, message=str(exc), ats="amazon")


def _amazon_sign_in(
    page: Page,
    email: str,
    password: str,
    profile: ApplicationProfile,
) -> None:
    human_type(page, ["input[type='email']", "input[name='email']"], email)
    if password:
        human_type(page, ["input[type='password']", "input[name='password']"], password)

    if click_first_visible(
        page,
        [
            "button:has-text('Sign in')",
            "button:has-text('Sign In')",
            "input[type='submit']",
        ],
        timeout_ms=4000,
    ):
        human_pause(page, 2500, 4000)
        return

    click_first_visible(
        page,
        [
            "a:has-text('Create account')",
            "button:has-text('Create account')",
            "a:has-text('Register')",
        ],
        timeout_ms=3000,
    )
    human_pause(page, 1000, 2000)

    human_type(page, ["input[name='firstName']"], profile.first_name)
    human_type(page, ["input[name='lastName']"], profile.last_name)
    if password:
        human_type(page, ["input[type='password']"], password)

    click_first_visible(
        page,
        [
            "button:has-text('Create account')",
            "button:has-text('Register')",
            "button:has-text('Sign in')",
        ],
        timeout_ms=4000,
    )
    human_pause(page, 2500, 4000)

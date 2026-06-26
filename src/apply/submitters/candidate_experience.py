"""Shared Playwright flow for Workday + Oracle HCM Candidate Experience portals."""

from pathlib import Path

from playwright.sync_api import Page

from ..profile import ApplicationProfile
from .common import (
    SubmitResult,
    answer_work_authorization,
    click_first_visible,
    detect_submission_blocked,
    fill_first_visible,
    human_pause,
    human_type,
    save_failure_screenshot,
    upload_resume,
)

APPLY_SELECTORS = [
    "a[data-automation-id='jobPostingApplyButton']",
    "button[data-automation-id='jobPostingApplyButton']",
    "button:has-text('Apply Manually')",
    "a:has-text('Apply Manually')",
    "button:has-text('Apply')",
    "a:has-text('Apply')",
]

NEXT_SELECTORS = [
    "button[data-automation-id='bottom-navigation-next-button']",
    "button[data-automation-id='pageFooterNextButton']",
    "button:has-text('Save and Continue')",
    "button:has-text('Continue')",
    "button:has-text('Next')",
]

SUBMIT_SELECTORS = [
    "button[data-automation-id='bottom-navigation-submit-button']",
    "button[data-automation-id='pageFooterSubmitButton']",
    "button:has-text('Submit')",
    "button:has-text('Submit Application')",
]

SUCCESS_MARKERS = (
    "submitted",
    "thank you",
    "application received",
    "successfully submitted",
    "we received your application",
)


def submit_candidate_experience(
    page: Page,
    job_url: str,
    resume_path: Path,
    profile: ApplicationProfile,
    credentials: dict,
    *,
    ats: str,
) -> SubmitResult:
    email = credentials.get("email") or profile.email
    password = credentials.get("password", "")

    page.goto(job_url, wait_until="domcontentloaded", timeout=90000)
    human_pause(page, 2000, 3500)

    click_first_visible(page, APPLY_SELECTORS, timeout_ms=10000)
    human_pause(page, 1500, 2500)

    # Prefer manual apply over LinkedIn / Indeed import when offered.
    click_first_visible(
        page,
        [
            "button:has-text('Apply Manually')",
            "a:has-text('Apply Manually')",
            "button:has-text('I already have an account')",
        ],
        timeout_ms=4000,
    )
    human_pause(page, 1000, 2000)

    _login_or_register(page, email, password, profile)
    human_pause(page, 1500, 2500)

    for _ in range(15):
        _fill_current_page(page, profile, email)
        human_pause(page, 500, 1000)
        upload_resume(page, resume_path)
        human_pause(page, 800, 1400)
        answer_work_authorization(page, profile.needs_sponsorship)
        _accept_checkboxes(page)
        human_pause(page, 400, 800)

        blocked = detect_submission_blocked(page)
        if blocked:
            save_failure_screenshot(page, resume_path.parent, f"{ats}_blocked")
            return SubmitResult(
                success=False,
                message=f"{ats} blocked submission: {blocked}",
                ats=ats,
                blocked=True,
            )

        if click_first_visible(page, SUBMIT_SELECTORS, timeout_ms=3000):
            human_pause(page, 4000, 6000)
            blocked = detect_submission_blocked(page)
            if blocked:
                save_failure_screenshot(page, resume_path.parent, f"{ats}_blocked")
                return SubmitResult(
                    success=False,
                    message=f"{ats} blocked submission: {blocked}",
                    ats=ats,
                    blocked=True,
                )
            content = page.content().lower()
            if any(marker in content for marker in SUCCESS_MARKERS):
                return SubmitResult(
                    success=True,
                    message=f"{ats} application submitted.",
                    ats=ats,
                )
            # Submit clicked but no confirmation — keep trying pages.
            human_pause(page, 1000, 2000)

        if click_first_visible(page, NEXT_SELECTORS, timeout_ms=3000):
            human_pause(page, 2000, 3500)
            continue

        content = page.content().lower()
        if any(marker in content for marker in SUCCESS_MARKERS):
            return SubmitResult(
                success=True,
                message=f"{ats} application submitted.",
                ats=ats,
            )
        break

    save_failure_screenshot(page, resume_path.parent, f"{ats}_failed")
    return SubmitResult(
        success=False,
        message=f"{ats} multi-page flow did not complete.",
        ats=ats,
    )


def _login_or_register(
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
            "button:has-text('Sign In')",
            "button[data-automation-id='signInSubmitButton']",
            "button:has-text('Sign in')",
        ],
        timeout_ms=4000,
    ):
        human_pause(page, 2500, 4000)
        return

    click_first_visible(
        page,
        [
            "button:has-text('Create Account')",
            "button:has-text('Register')",
            "button[data-automation-id='createAccountSubmitButton']",
            "a:has-text('Create Account')",
        ],
        timeout_ms=4000,
    )
    human_pause(page, 1000, 2000)

    human_type(page, ["input[name='firstName']", "input[data-automation-id='firstName']"], profile.first_name)
    human_type(page, ["input[name='lastName']", "input[data-automation-id='lastName']"], profile.last_name)
    if password:
        human_type(page, ["input[name='password']"], password)
        human_type(page, ["input[name='verifyPassword']"], password)

    click_first_visible(
        page,
        [
            "button:has-text('Create Account')",
            "button[data-automation-id='createAccountSubmitButton']",
            "button:has-text('Sign In')",
        ],
        timeout_ms=4000,
    )
    human_pause(page, 2500, 4000)


def _fill_current_page(page: Page, profile: ApplicationProfile, email: str) -> None:
    human_type(page, ["input[name='firstName']", "input[data-automation-id='firstName']"], profile.first_name)
    human_type(page, ["input[name='lastName']", "input[data-automation-id='lastName']"], profile.last_name)
    human_type(page, ["input[type='email']", "input[name='email']"], email)
    human_type(page, ["input[type='tel']", "input[name='phoneNumber']"], profile.phone)
    fill_first_visible(page, ["input[name='addressLine1']"], profile.street)
    human_type(page, ["input[name='city']"], profile.city)
    fill_first_visible(page, ["input[name='postalCode']"], profile.zip_code)

    if profile.linkedin_url:
        human_type(
            page,
            [
                "input[name*='linkedin']",
                "input[placeholder*='LinkedIn']",
                "input[aria-label*='LinkedIn']",
            ],
            profile.linkedin_url,
        )

    for selector in ("select[name='country']", "select[data-automation-id='country']"):
        try:
            page.locator(selector).first.select_option(label=profile.country)
            break
        except Exception:
            pass
    for selector in ("select[name='state']", "select[data-automation-id='state']"):
        try:
            page.locator(selector).first.select_option(label=profile.state)
            break
        except Exception:
            pass


def _accept_checkboxes(page: Page) -> None:
    for checkbox in page.locator("input[type='checkbox']").all():
        try:
            if checkbox.is_visible(timeout=500) and not checkbox.is_checked():
                checkbox.check(timeout=2000)
                human_pause(page, 200, 400)
        except Exception:
            continue

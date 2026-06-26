import random
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout


@dataclass
class SubmitResult:
    success: bool
    message: str
    ats: str = ""
    blocked: bool = False


BLOCKED_SUBMISSION_MARKERS = (
    "flagged as possible spam",
    "couldn't submit your application",
    "could not submit your application",
    "possible spam",
    "verify you are human",
    "complete the captcha",
    "too many submissions",
    "rate limit",
    "unusual activity",
)


def detect_submission_blocked(page: Page) -> str:
    """Return a reason if the ATS rejected the submission (spam, captcha, etc.)."""
    try:
        content = page.content().lower()
    except Exception:
        return ""
    for marker in BLOCKED_SUBMISSION_MARKERS:
        if marker in content:
            return marker
    try:
        alert = page.locator("[role='alert'], .error, [class*='error']").first
        if alert.is_visible(timeout=500):
            text = (alert.inner_text(timeout=500) or "").lower()
            for marker in BLOCKED_SUBMISSION_MARKERS:
                if marker in text:
                    return marker
    except Exception:
        pass
    return ""


def human_pause(page: Page, min_ms: int = 400, max_ms: int = 1200) -> None:
    page.wait_for_timeout(random.randint(min_ms, max_ms))


def human_type(page: Page, selectors: list[str], value: str) -> bool:
    if not value:
        return False
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=2000):
                locator.click(timeout=2000)
                locator.fill("", timeout=1000)
                locator.type(value, delay=random.randint(40, 90), timeout=15000)
                human_pause(page, 200, 500)
                return True
        except (PlaywrightTimeout, Exception):
            continue
    return False


def save_failure_screenshot(page: Page, output_dir: Path, label: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{label}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass


def click_first_visible(page: Page, selectors: list[str], timeout_ms: int = 5000) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=timeout_ms):
                locator.click(timeout=timeout_ms)
                return True
        except (PlaywrightTimeout, Exception):
            continue
    return False


def fill_first_visible(page: Page, selectors: list[str], value: str) -> bool:
    if not value:
        return False
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=2000):
                locator.fill(value, timeout=3000)
                return True
        except (PlaywrightTimeout, Exception):
            continue
    return False


def upload_resume(page: Page, resume_path: Path) -> bool:
    selectors = [
        "input[type='file']",
        "input[accept*='pdf']",
        "input[accept*='doc']",
        "input[data-automation-id='file-upload-input-ref']",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.set_input_files(str(resume_path), timeout=10000)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def answer_work_authorization(page: Page, needs_sponsorship: bool) -> None:
    """Best-effort; never raises — optional questions vary per company."""
    try:
        _answer_yes_no_near_text(
            page,
            [
                "authorized to work",
                "legally authorized",
                "eligible to work",
                "work authorization",
            ],
            answer_yes=True,
        )
        _answer_yes_no_near_text(
            page,
            [
                "require sponsorship",
                "need sponsorship",
                "visa sponsorship",
                "immigration sponsorship",
            ],
            answer_yes=needs_sponsorship,
        )
        if not needs_sponsorship:
            for phrase in (
                "will not require sponsorship",
                "do not require sponsorship",
                "not require sponsorship",
            ):
                try:
                    page.locator(f"label:has-text('{phrase}')").first.click(timeout=2000)
                except Exception:
                    pass
    except Exception:
        pass


def _answer_yes_no_near_text(
    page: Page, question_phrases: list[str], *, answer_yes: bool
) -> bool:
    answer = "Yes" if answer_yes else "No"
    for phrase in question_phrases:
        try:
            question = page.get_by_text(phrase, exact=False).first
            if not question.is_visible(timeout=1500):
                continue
            group = question.locator(
                "xpath=ancestor::*[self::div or self::fieldset or self::li][position()<=4][1]"
            )
            radio = group.get_by_role("radio", name=answer, exact=True)
            if radio.count() > 0:
                radio.first.click(timeout=4000)
                return True
            label = group.locator(f"label:has-text('{answer}')").first
            if label.is_visible(timeout=1000):
                label.click(timeout=3000)
                return True
        except Exception:
            continue
    return False


def fill_standard_contact(page: Page, profile, email: str) -> None:
    human_type(
        page,
        ["input[name='first_name']", "input[id*='firstName']", "#first_name"],
        profile.first_name,
    )
    human_type(
        page,
        ["input[name='last_name']", "input[id*='lastName']", "#last_name"],
        profile.last_name,
    )
    human_type(
        page,
        ["input[name='email']", "input[type='email']", "#email"],
        email,
    )
    human_type(
        page,
        ["input[name='phone']", "input[type='tel']", "#phone", "input[name='phone_number']"],
        profile.phone,
    )
    human_type(page, ["input[name='location']", "#location"], profile.city)
    if profile.linkedin_url:
        human_type(
            page,
            [
                "input[name='urls[LinkedIn]']",
                "input[placeholder*='LinkedIn']",
                "input[name*='linkedin']",
            ],
            profile.linkedin_url,
        )

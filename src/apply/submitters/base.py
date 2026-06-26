from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from ...config import DATA_DIR
from ..profile import ApplicationProfile
from .common import SubmitResult, save_failure_screenshot


class BaseSubmitter:
    ats_name = "base"

    def submit(
        self,
        page: Page,
        job_url: str,
        resume_path: Path,
        profile: ApplicationProfile,
        credentials: dict,
    ) -> SubmitResult:
        raise NotImplementedError


@dataclass
class ApplyBrowserSession:
    """Reuses one browser profile across applications to look less bot-like."""

    headless: bool
    slow_mo: int = 100
    user_data_dir: Optional[Path] = None
    _playwright: Optional[Playwright] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None

    def is_alive(self) -> bool:
        try:
            return (
                self._page is not None
                and self._context is not None
                and not self._page.is_closed()
            )
        except Exception:
            return False

    def reset(self) -> None:
        """Tear down and relaunch — e.g. after the user closes the browser window."""
        self.close()

    def get_page(self) -> Page:
        if self.is_alive():
            return self._page  # type: ignore[return-value]
        self._launch()
        return self._page  # type: ignore[return-value]

    def _launch(self) -> None:
        self._playwright = sync_playwright().start()
        profile_dir = self.user_data_dir or (DATA_DIR / "browser_profile")
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/Chicago",
        )
        self._page = (
            self._context.pages[0]
            if self._context.pages
            else self._context.new_page()
        )

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._page = None


def _browser_closed_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "closed" in message or "target page" in message


def run_with_browser(
    headless: bool,
    fn: Callable,
    *,
    profile: ApplicationProfile,
    job_url: str,
    resume_path: Path,
    credentials: dict,
    ats: str,
    browser_session: Optional[ApplyBrowserSession] = None,
    slow_mo: int = 100,
) -> SubmitResult:
    screenshots_dir = DATA_DIR / "applications" / "errors"
    owns_session = browser_session is None
    if owns_session:
        browser_session = ApplyBrowserSession(headless=headless, slow_mo=slow_mo)

    last_exc: Optional[Exception] = None
    for attempt in range(2):
        page = browser_session.get_page()
        try:
            return fn(page, job_url, resume_path, profile, credentials)
        except Exception as exc:
            last_exc = exc
            if owns_session or attempt > 0 or not _browser_closed_error(exc):
                save_failure_screenshot(page, screenshots_dir, f"{ats}_error")
                return SubmitResult(success=False, message=str(exc), ats=ats)
            browser_session.reset()

    return SubmitResult(
        success=False,
        message=str(last_exc or "browser session failed"),
        ats=ats,
    )

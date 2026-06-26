import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from ..application_store import ApplicationStore
from ..config import DATA_DIR, load_settings
from ..filters import job_matches_filters, matches_experience
from ..models import JobPosting
from ..monitor import fetch_all_jobs
from ..store import JobStore
from .ats_detect import detect_ats
from .eligibility import is_eligible_for_apply
from .job_description import fetch_job_description
from .match_score import score_resume_match
from .profile import load_application_profile
from .resume_tailor import read_resume_text, resolve_base_resume, tailor_resume
from .status_checker import check_role_status
from .submitters import submit_application
from .submitters.base import ApplyBrowserSession

logger = logging.getLogger(__name__)


def is_apply_window(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(ZoneInfo("America/Chicago"))
    return now.hour == 8 and now.minute < 30


def _already_ran_today() -> bool:
    marker = DATA_DIR / "apply_agent_last_run.txt"
    if not marker.exists():
        return False
    today = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")
    return marker.read_text().strip() == today


def _mark_ran_today() -> None:
    marker = DATA_DIR / "apply_agent_last_run.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")
    marker.write_text(today)


def _eligible_jobs(jobs: list[JobPosting], settings: dict) -> list[JobPosting]:
    filtered = [job for job in jobs if job_matches_filters(job, settings)]
    exp_max = int(settings.get("experience_max_years", 5))
    logger.info(
        "Matched %d job(s) for apply-agent filters "
        "(US / role / posting-time / experience 0-%d yrs).",
        len(filtered),
        exp_max,
    )
    return filtered


def _sort_by_ats_priority(
    jobs: list[JobPosting], priority: list[str]
) -> list[JobPosting]:
    rank = {name: index for index, name in enumerate(priority)}

    def sort_key(job: JobPosting) -> tuple[int, str]:
        ats = detect_ats(job)
        if ats in rank:
            return (rank[ats], job.company)
        return (len(priority), job.company)

    return sorted(jobs, key=sort_key)


def refresh_role_statuses(app_store: ApplicationStore, settings: dict) -> None:
    for record in app_store.applications_for_status_check():
        role_status = check_role_status(record.url, settings)
        app_store.update_role_status(record.id, role_status)
        logger.info(
            "Role status for %s — %s: %s",
            record.company,
            record.title,
            role_status,
        )


def run_apply_agent(
    *,
    dry_run: bool = False,
    force: bool = False,
    check_status_only: bool = False,
) -> int:
    settings = load_settings()
    apply_cfg = settings["apply_agent"]

    if not apply_cfg.get("enabled", True):
        logger.info("Apply agent is disabled in config.")
        return 0

    if not force and not check_status_only and not is_apply_window():
        logger.info("Outside 8:00 AM CST apply window. Use --force to run now.")
        return 0

    if not force and not check_status_only and _already_ran_today():
        logger.info("Apply agent already ran today.")
        return 0

    profile_data = apply_cfg.get("profile") or {}
    if not profile_data:
        logger.error("Missing application_profile.yaml")
        return 1
    profile = load_application_profile(profile_data)

    if settings.get("experience_filter_enabled", True):
        logger.info(
            "Experience filter active: %d–%d years (skips senior / higher-experience roles).",
            int(settings.get("experience_min_years", 0)),
            int(settings.get("experience_max_years", 5)),
        )

    app_store = ApplicationStore(DATA_DIR / "applications.db")
    job_store = JobStore(DATA_DIR / "seen_jobs.db")
    base_resume = Path(apply_cfg["base_resume_path"])
    if not base_resume.is_absolute():
        base_resume = DATA_DIR.parent / base_resume
    base_resume = resolve_base_resume(base_resume)

    try:
        if check_status_only:
            refresh_role_statuses(app_store, settings)
            return 0

        refresh_role_statuses(app_store, settings)

        fetched = fetch_all_jobs(settings)
        candidates = _sort_by_ats_priority(
            _eligible_jobs(fetched, settings),
            apply_cfg.get("ats_priority", []),
        )
        resume_text = read_resume_text(base_resume)

        processed = 0
        skipped = 0
        applied_count = 0
        max_per_day = int(apply_cfg.get("max_applications_per_day", 25))
        min_score = float(apply_cfg.get("min_match_score", 85))
        auto_submit = bool(apply_cfg.get("auto_submit", True))
        ats_priority = set(apply_cfg.get("ats_priority", []))
        headless = bool(apply_cfg.get("playwright_headless", True))
        match_mode = str(apply_cfg.get("match_mode", "auto"))
        resume_mode = str(apply_cfg.get("resume_mode", "preserve"))
        max_per_company = int(apply_cfg.get("max_applications_per_company", 1))
        delay_seconds = int(apply_cfg.get("delay_between_applications_seconds", 60))
        delay_jitter = int(apply_cfg.get("delay_jitter_seconds", 30))
        slow_mo = int(apply_cfg.get("playwright_slow_mo", 100))
        blocked_companies: set[str] = set()
        attempted_companies: set[str] = set()
        browser_session: Optional[ApplyBrowserSession] = None

        if auto_submit and not dry_run:
            browser_session = ApplyBrowserSession(
                headless=headless,
                slow_mo=slow_mo,
            )

        try:
            for job in candidates:
                if processed >= max_per_day:
                    logger.info("Reached daily application limit (%d).", max_per_day)
                    break
                if app_store.has_application(job.id):
                    continue

                if job.company in blocked_companies:
                    skipped += 1
                    logger.info(
                        "Skipped %s — %s (company blocked after spam detection earlier today)",
                        job.company,
                        job.title,
                    )
                    continue

                if job.company in attempted_companies:
                    skipped += 1
                    logger.info(
                        "Skipped %s — %s (already attempted this company in this run)",
                        job.company,
                        job.title,
                    )
                    continue

                if (
                    app_store.submit_attempt_count_for_company_today(job.company)
                    >= max_per_company
                ):
                    skipped += 1
                    logger.info(
                        "Skipped %s — %s (already attempted %d role(s) at this company today)",
                        job.company,
                        job.title,
                        max_per_company,
                    )
                    continue

                description = fetch_job_description(job, settings)
                ats = detect_ats(job) or ""

                if settings.get("experience_filter_enabled", True) and not matches_experience(
                    job,
                    min_years=int(settings.get("experience_min_years", 0)),
                    max_years=int(settings.get("experience_max_years", 5)),
                    extra_text=description,
                ):
                    skipped += 1
                    logger.info(
                        "Skipped %s — %s (experience out of range)",
                        job.company,
                        job.title,
                    )
                    if not dry_run:
                        app_store.insert_application(
                            job_id=job.id,
                            company=job.company,
                            title=job.title,
                            url=job.url,
                            location=job.location,
                            match_score=0,
                            job_description=description,
                            resume_path="n/a",
                            status="skipped",
                            skip_reason="experience_out_of_range",
                            ats_type=ats,
                        )
                    continue

                eligible, reason = is_eligible_for_apply(
                    job.title,
                    description,
                    needs_sponsorship=profile.needs_sponsorship,
                )
                if not eligible:
                    skipped += 1
                    logger.info("Skipped %s — %s (%s)", job.company, job.title, reason)
                    if not dry_run:
                        app_store.insert_application(
                            job_id=job.id,
                            company=job.company,
                            title=job.title,
                            url=job.url,
                            location=job.location,
                            match_score=0,
                            job_description=description,
                            resume_path="n/a",
                            status="skipped",
                            skip_reason=reason,
                            ats_type=ats,
                        )
                    continue

                score, summary = score_resume_match(
                    resume_text,
                    job.title,
                    description,
                    min_score=min_score,
                    mode=match_mode,
                )
                if score < min_score:
                    skipped += 1
                    logger.info(
                        "Skipped %s — %s (match %.1f%% < %.1f%%): %s",
                        job.company,
                        job.title,
                        score,
                        min_score,
                        summary,
                    )
                    continue

                logger.info(
                    "Processing %s — %s (match %.1f%%, ATS: %s)",
                    job.company,
                    job.title,
                    score,
                    ats or "unknown",
                )

                if dry_run:
                    print(
                        f"[APPLY] {job.company} — {job.title} "
                        f"({score:.1f}% match, ATS={ats})\n        {job.url}"
                    )
                    processed += 1
                    continue

                resume_path, tailor_note = tailor_resume(
                    base_resume,
                    job.title,
                    job.company,
                    description,
                    DATA_DIR / "applications",
                    mode=resume_mode,
                )
                logger.info("Resume: %s (%s)", resume_path, tailor_note)

                status = "prepared"
                submit_message = ""
                skip_reason = ""

                if auto_submit and ats and ats in ats_priority:
                    if not settings["apply_credentials"].get("email"):
                        status = "failed"
                        submit_message = "APPLY_EMAIL not configured"
                        logger.warning("APPLY_EMAIL not set; cannot auto-submit.")
                    else:
                        logger.info("Auto-submitting to %s for %s...", ats, job.company)
                        result = submit_application(
                            ats,
                            job,
                            resume_path,
                            profile,
                            settings["apply_credentials"],
                            headless=headless,
                            browser_session=browser_session,
                            slow_mo=slow_mo,
                        )
                        submit_message = result.message
                        if result.success:
                            status = "applied"
                            applied_count += 1
                            logger.info(
                                "Applied to %s — %s",
                                job.company,
                                job.title,
                            )
                            if applied_count < max_per_day and delay_seconds > 0:
                                wait = delay_seconds + random.randint(0, delay_jitter)
                                logger.info(
                                    "Waiting %ds before next application (anti-spam delay)...",
                                    wait,
                                )
                                time.sleep(wait)
                        else:
                            status = "failed"
                            if getattr(result, "blocked", False):
                                blocked_companies.add(job.company)
                                logger.error(
                                    "Blocked by %s for %s — skipping remaining %s roles this run.",
                                    ats,
                                    job.title,
                                    job.company,
                                )
                            elif "closed" in result.message.lower() and browser_session:
                                logger.warning(
                                    "Browser was closed during %s — relaunching for next application.",
                                    job.company,
                                )
                                browser_session.reset()
                            logger.error(
                                "Auto-submit failed for %s — %s: %s",
                                job.company,
                                job.title,
                                result.message,
                            )
                        attempted_companies.add(job.company)
                elif auto_submit:
                    status = "failed"
                    submit_message = f"unsupported_ats:{ats or 'unknown'}"

                app_store.insert_application(
                    job_id=job.id,
                    company=job.company,
                    title=job.title,
                    url=job.url,
                    location=job.location,
                    match_score=score,
                    job_description=description,
                    resume_path=str(resume_path),
                    status=status,
                    skip_reason=skip_reason,
                    ats_type=ats,
                    submit_message=submit_message,
                )
                job_store.mark_seen(job)
                processed += 1

            logger.info(
                "Apply agent finished. Processed %d, applied %d, skipped %d. "
                "View DB: python run_apply.py --list",
                processed,
                applied_count,
                skipped,
            )
            if not dry_run and not check_status_only and (force or is_apply_window()):
                _mark_ran_today()
            return 0
        finally:
            if browser_session is not None:
                browser_session.close()
    finally:
        app_store.close()
        job_store.close()

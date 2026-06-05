import logging
import sys

from .config import DATA_DIR, load_settings
from .filters import job_matches_filters
from .models import JobPosting
from .notifier import send_email
from .scrapers import SCRAPERS
from .store import JobStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def fetch_all_jobs(settings: dict) -> list[JobPosting]:
    all_jobs: list[JobPosting] = []

    for company_cfg in settings["companies"]:
        company_name = company_cfg["name"]
        for source in company_cfg.get("sources", []):
            source_type = source.get("type")
            scraper = SCRAPERS.get(source_type)
            if not scraper:
                logger.warning("Unknown source type %s for %s", source_type, company_name)
                continue

            try:
                jobs = scraper(company_name, source, settings)
                logger.info(
                    "Fetched %d jobs from %s (%s)",
                    len(jobs),
                    company_name,
                    source_type,
                )
                all_jobs.extend(jobs)
            except Exception:
                logger.exception(
                    "Failed to fetch %s for %s",
                    source_type,
                    company_name,
                )

    return all_jobs


def run(dry_run: bool = False, seed: bool = False) -> int:
    settings = load_settings()
    store = JobStore(DATA_DIR / "seen_jobs.db")

    try:
        fetched = fetch_all_jobs(settings)
        matching = [job for job in fetched if job_matches_filters(job, settings)]
        logger.info(
            "Matched %d job(s) after US / role / posting-time filters.",
            len(matching),
        )
        new_jobs = [job for job in matching if store.is_new(job)]

        if not new_jobs:
            logger.info("No new job postings found.")
            return 0

        logger.info("Found %d new job posting(s).", len(new_jobs))

        if dry_run:
            for job in new_jobs:
                print(f"[NEW] {job.company} — {job.title}\n       {job.url}")
            return 0

        if seed:
            for job in matching:
                store.mark_seen(job)
            logger.info(
                "Seeded database with %d job(s); no email sent.", len(matching)
            )
            return 0

        send_email(new_jobs, settings["smtp"])
        for job in new_jobs:
            store.mark_seen(job)

        logger.info("Notification sent for %d job(s).", len(new_jobs))
        return 0
    finally:
        store.close()


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    seed = "--seed" in sys.argv
    raise SystemExit(run(dry_run=dry_run, seed=seed))

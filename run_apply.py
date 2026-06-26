#!/usr/bin/env python3
import logging
import sys
from pathlib import Path

from src.application_store import ApplicationStore
from src.apply.agent import run_apply_agent
from src.apply.resume_tailor import resolve_base_resume
from src.config import DATA_DIR, load_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


def list_applications() -> None:
    store = ApplicationStore(DATA_DIR / "applications.db")
    try:
        rows = store.list_applications(limit=100)
        if not rows:
            print("No applications tracked yet.")
            return
        for row in rows:
            print("-" * 72)
            print(f"ID:          {row.id}")
            print(f"Date:        {row.created_at}")
            print(f"Company:     {row.company}")
            print(f"Role:        {row.title}")
            print(f"Status:      {row.status}")
            print(f"Role open:   {row.role_status}")
            print(f"ATS:         {row.ats_type or 'n/a'}")
            print(f"Match:       {row.match_score:.1f}%")
            print(f"Applied at:  {row.applied_at or 'n/a'}")
            if row.resume_path and row.resume_path != "n/a":
                print(f"Resume:      {row.resume_path}")
            if row.submit_message:
                print(f"Submit note: {row.submit_message}")
            if row.skip_reason:
                print(f"Skip reason: {row.skip_reason}")
            print(f"URL:         {row.url}")
    finally:
        store.close()


def main() -> None:
    args = sys.argv[1:]
    if "--list" in args:
        list_applications()
        raise SystemExit(0)

    dry_run = "--dry-run" in args
    force = "--force" in args
    check_status_only = "--check-status" in args

    base_resume = Path(load_settings()["apply_agent"]["base_resume_path"])
    if not base_resume.is_absolute():
        base_resume = DATA_DIR.parent / base_resume
    try:
        base_resume = resolve_base_resume(base_resume)
    except FileNotFoundError as exc:
        print(exc)
        raise SystemExit(1)

    raise SystemExit(
        run_apply_agent(
            dry_run=dry_run,
            force=force,
            check_status_only=check_status_only,
        )
    )


if __name__ == "__main__":
    main()

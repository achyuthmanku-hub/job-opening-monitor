#!/usr/bin/env python3
"""Seed the shared job pool (scan → enrich → parse → embed).

Use against a remote deploy so friends have jobs to match:

  export DATABASE_URL='postgresql://...@dpg-xxx.render.com/job_monitor'
  python scripts/seed_job_pool.py

Long-running; do not rely on an HTTP request to /jobs/scan on free hosts.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("seed_job_pool")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed remote/local job pool")
    parser.add_argument("--store-all", action="store_true", help="Skip title/US filters")
    parser.add_argument("--skip-enrich", action="store_true")
    parser.add_argument("--skip-parse", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    from api.services.descriptions import enrich_descriptions
    from api.services.ingest import ingest_jobs
    from api.services.nlp_pipeline import parse_jobs
    from api.services.rag_pipeline import embed_jobs
    from src.config import load_settings
    from src.db import SessionLocal, get_database_url

    logger.info("DATABASE_URL host target: %s", get_database_url().split("@")[-1])
    settings = load_settings()
    db = SessionLocal()
    try:
        summary = ingest_jobs(db, settings, store_all=args.store_all)
        logger.info("Ingest: %s", summary)

        if not args.skip_enrich:
            n = enrich_descriptions(db, limit=args.limit)
            logger.info("Descriptions enriched: %s", n)

        if not args.skip_parse:
            parsed = parse_jobs(db, limit=args.limit)
            logger.info("NLP parse: %s", parsed)

        if not args.skip_embed:
            embedded = embed_jobs(db, limit=args.limit, only_unembedded=True)
            logger.info("Embed: %s", embedded)

        logger.info("Done. Friends can upload resumes at /ui/upload")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

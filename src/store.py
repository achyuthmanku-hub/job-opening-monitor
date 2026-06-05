import json
import sqlite3
from pathlib import Path

from .models import JobPosting


class JobStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                first_seen TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self.conn.commit()

    def is_new(self, job: JobPosting) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job.id,)
        ).fetchone()
        return row is None

    def mark_seen(self, job: JobPosting) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO seen_jobs (job_id, company, title, url, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job.id, job.company, job.title, job.url, job.source),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

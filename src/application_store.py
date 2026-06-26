import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ApplicationRecord:
    id: int
    job_id: str
    company: str
    title: str
    url: str
    location: str
    match_score: float
    job_description: str
    resume_path: str
    status: str
    role_status: str
    skip_reason: str
    applied_at: Optional[str]
    created_at: str
    updated_at: str
    last_status_check: Optional[str]
    ats_type: str = ""
    submit_message: str = ""


class ApplicationStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._migrate_schema()
        self.conn.commit()

    def _migrate_schema(self) -> None:
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
        ).fetchone()
        if not row:
            self._create_schema()
            return

        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(applications)").fetchall()
        }
        base_columns = {
            "id",
            "job_id",
            "company",
            "title",
            "url",
            "resume_path",
            "status",
            "created_at",
        }
        if base_columns.issubset(columns):
            self._ensure_columns(columns)
            return

        self.conn.execute("ALTER TABLE applications RENAME TO applications_legacy")
        self._create_schema()
        legacy_columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(applications_legacy)").fetchall()
        }
        if legacy_columns:
            resume_col = (
                "tailored_resume_path"
                if "tailored_resume_path" in legacy_columns
                else "resume_path"
                if "resume_path" in legacy_columns
                else None
            )
            resume_expr = f"COALESCE({resume_col}, 'n/a')" if resume_col else "'n/a'"
            self.conn.execute(
                f"""
                INSERT INTO applications (
                    job_id, company, title, url, resume_path, status,
                    skip_reason, applied_at, updated_at
                )
                SELECT
                    job_id, company, title, url,
                    {resume_expr},
                    status,
                    COALESCE(skip_reason, ''),
                    applied_at,
                    COALESCE(updated_at, datetime('now'))
                FROM applications_legacy
                """
            )
        self.conn.execute("DROP TABLE applications_legacy")
        self._ensure_columns(
            {row[1] for row in self.conn.execute("PRAGMA table_info(applications)").fetchall()}
        )

    def _ensure_columns(self, existing: set[str]) -> None:
        if "location" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN location TEXT DEFAULT ''"
            )
        if "match_score" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN match_score REAL"
            )
        if "job_description" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN job_description TEXT DEFAULT ''"
            )
        if "role_status" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN role_status TEXT DEFAULT 'open'"
            )
        if "skip_reason" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN skip_reason TEXT DEFAULT ''"
            )
        if "applied_at" not in existing:
            self.conn.execute("ALTER TABLE applications ADD COLUMN applied_at TEXT")
        if "updated_at" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN updated_at TEXT DEFAULT (datetime('now'))"
            )
        if "last_status_check" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN last_status_check TEXT"
            )
        if "ats_type" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN ats_type TEXT DEFAULT ''"
            )
        if "submit_message" not in existing:
            self.conn.execute(
                "ALTER TABLE applications ADD COLUMN submit_message TEXT DEFAULT ''"
            )

    def _create_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                location TEXT DEFAULT '',
                match_score REAL,
                job_description TEXT DEFAULT '',
                resume_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'prepared',
                role_status TEXT NOT NULL DEFAULT 'open',
                skip_reason TEXT DEFAULT '',
                applied_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_status_check TEXT,
                ats_type TEXT DEFAULT '',
                submit_message TEXT DEFAULT ''
            )
            """
        )

    def has_application(self, job_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None

    def applied_count_for_company_today(self, company: str) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) FROM applications
            WHERE company = ?
              AND status = 'applied'
              AND date(created_at) = date('now', 'localtime')
            """,
            (company,),
        ).fetchone()
        return int(row[0]) if row else 0

    def submit_attempt_count_for_company_today(self, company: str) -> int:
        """Applied or failed auto-submit attempts today (one company, one try per day)."""
        row = self.conn.execute(
            """
            SELECT COUNT(*) FROM applications
            WHERE company = ?
              AND status IN ('applied', 'failed')
              AND resume_path != 'n/a'
              AND date(created_at) = date('now', 'localtime')
            """,
            (company,),
        ).fetchone()
        return int(row[0]) if row else 0

    def insert_application(
        self,
        *,
        job_id: str,
        company: str,
        title: str,
        url: str,
        location: str,
        match_score: float,
        job_description: str,
        resume_path: str,
        status: str = "prepared",
        skip_reason: str = "",
        ats_type: str = "",
        submit_message: str = "",
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO applications (
                job_id, company, title, url, location, match_score,
                job_description, resume_path, status, skip_reason,
                ats_type, submit_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                company,
                title,
                url,
                location,
                match_score,
                job_description,
                resume_path,
                status,
                skip_reason,
                ats_type,
                submit_message,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def update_status(
        self,
        application_id: int,
        status: str,
        skip_reason: str = "",
        submit_message: str = "",
    ) -> None:
        self.conn.execute(
            """
            UPDATE applications
            SET status = ?,
                skip_reason = CASE WHEN ? = '' THEN skip_reason ELSE ? END,
                submit_message = CASE WHEN ? = '' THEN submit_message ELSE ? END,
                applied_at = CASE WHEN ? = 'applied' THEN datetime('now') ELSE applied_at END,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                status,
                skip_reason,
                skip_reason,
                submit_message,
                submit_message,
                status,
                application_id,
            ),
        )
        self.conn.commit()

    def mark_applied(self, application_id: int) -> None:
        self.conn.execute(
            """
            UPDATE applications
            SET status = 'applied',
                applied_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (application_id,),
        )
        self.conn.commit()

    def update_role_status(self, application_id: int, role_status: str) -> None:
        self.conn.execute(
            """
            UPDATE applications
            SET role_status = ?,
                last_status_check = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (role_status, application_id),
        )
        self.conn.commit()

    def list_applications(self, limit: int = 50) -> list[ApplicationRecord]:
        rows = self.conn.execute(
            """
            SELECT * FROM applications
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def applications_for_status_check(self) -> list[ApplicationRecord]:
        rows = self.conn.execute(
            """
            SELECT * FROM applications
            WHERE status IN ('prepared', 'applied')
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> ApplicationRecord:
        return ApplicationRecord(
            id=row["id"],
            job_id=row["job_id"],
            company=row["company"],
            title=row["title"],
            url=row["url"],
            location=row["location"] or "",
            match_score=float(row["match_score"] or 0),
            job_description=row["job_description"] or "",
            resume_path=row["resume_path"],
            status=row["status"],
            role_status=row["role_status"],
            skip_reason=row["skip_reason"] or "",
            applied_at=row["applied_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_status_check=row["last_status_check"],
            ats_type=row["ats_type"] or "",
            submit_message=row["submit_message"] or "",
        )

    def close(self) -> None:
        self.conn.close()

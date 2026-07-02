import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Copy {path.stem}.example{path.suffix} and customize it."
        )
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _parse_year_value(value, default: int) -> int:
    if value is None:
        return default
    text = str(value).strip().rstrip("+")
    if "-" in text and not text.startswith("-"):
        text = text.split("-", 1)[1].strip().rstrip("+")
    return int(float(text))


def load_settings() -> dict:
    load_dotenv(ROOT / ".env")
    config = load_yaml(ROOT / "config.yaml")
    companies = load_yaml(ROOT / "companies.yaml")

    filters = config.get("filters", {})

    apply_cfg = config.get("apply_agent", {})

    profile = {}
    profile_path = ROOT / "application_profile.yaml"
    if profile_path.exists():
        profile = load_yaml(profile_path)

    return {
        "keywords": [k.lower() for k in config.get("keywords", [])],
        "us_only": filters.get("us_only", True),
        "posted_min_hours": float(filters.get("posted_min_hours", 1)),
        "posted_max_hours": float(filters.get("posted_max_hours", 5)),
        "allow_missing_posted_time": filters.get("allow_missing_posted_time", True),
        "experience_filter_enabled": filters.get("experience_filter_enabled", True),
        "experience_min_years": _parse_year_value(filters.get("experience_min_years"), 0),
        "experience_max_years": _parse_year_value(filters.get("experience_max_years"), 5),
        "request_timeout": config.get("request_timeout", 30),
        "user_agent": config.get(
            "user_agent", "JobOpeningMonitor/1.0 (+personal job alert bot)"
        ),
        "rate_limit": config.get("rate_limit", {}),
        "companies": companies.get("companies", []),
        "alerts": config.get("alerts", {}),
        "apply_agent": {
            "enabled": apply_cfg.get("enabled", True),
            "min_match_score": float(apply_cfg.get("min_match_score", 85)),
            "max_applications_per_day": int(
                apply_cfg.get("max_applications_per_day", 25)
            ),
            "timezone": apply_cfg.get("timezone", "America/Chicago"),
            "base_resume_path": apply_cfg.get(
                "base_resume_path", "data/resumes/base_resume.docx"
            ),
            "skip_clearance": apply_cfg.get("skip_clearance", True),
            "auto_submit": apply_cfg.get("auto_submit", True),
            "ats_priority": apply_cfg.get(
                "ats_priority",
                ["greenhouse", "ashby", "workday", "oracle", "amazon", "lever"],
            ),
            "playwright_headless": apply_cfg.get("playwright_headless", True),
            "playwright_slow_mo": int(apply_cfg.get("playwright_slow_mo", 100)),
            "max_applications_per_company": int(
                apply_cfg.get("max_applications_per_company", 1)
            ),
            "delay_between_applications_seconds": int(
                apply_cfg.get("delay_between_applications_seconds", 60)
            ),
            "delay_jitter_seconds": int(apply_cfg.get("delay_jitter_seconds", 30)),
            "match_mode": apply_cfg.get("match_mode", "auto"),
            "resume_mode": apply_cfg.get("resume_mode", "auto"),
            "profile": profile,
        },
        "apply_credentials": {
            "email": os.getenv("APPLY_EMAIL", os.getenv("SMTP_USER", "")).strip(),
            "password": os.getenv("APPLY_PASSWORD", "").strip(),
        },
        "smtp": {
            "host": os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "user": os.getenv("SMTP_USER", "").strip(),
            "password": os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip(),
            "notify_email": os.getenv("NOTIFY_EMAIL", "").strip(),
        },
        "api_auth_enabled": os.getenv("API_AUTH_ENABLED", "false").strip().lower()
        in ("1", "true", "yes"),
    }

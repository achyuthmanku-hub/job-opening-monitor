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


def load_settings() -> dict:
    load_dotenv(ROOT / ".env")
    config = load_yaml(ROOT / "config.yaml")
    companies = load_yaml(ROOT / "companies.yaml")

    filters = config.get("filters", {})

    return {
        "keywords": [k.lower() for k in config.get("keywords", [])],
        "us_only": filters.get("us_only", True),
        "posted_min_hours": float(filters.get("posted_min_hours", 1)),
        "posted_max_hours": float(filters.get("posted_max_hours", 5)),
        "request_timeout": config.get("request_timeout", 30),
        "user_agent": config.get(
            "user_agent", "JobOpeningMonitor/1.0 (+personal job alert bot)"
        ),
        "companies": companies.get("companies", []),
        "smtp": {
            "host": os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "user": os.getenv("SMTP_USER", "").strip(),
            "password": os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip(),
            "notify_email": os.getenv("NOTIFY_EMAIL", "").strip(),
        },
    }

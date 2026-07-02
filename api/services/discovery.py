import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.config import ROOT
from src.discovery.ats_detect_url import detect_ats, probe_careers_url
from src.discovery.company_store import add_company_to_yaml, import_pack_yaml, upsert_company_db

logger = logging.getLogger(__name__)
PACKS_DIR = ROOT / "data" / "company_packs"


def discover_company(
    db: Session,
    url: str,
    *,
    company_name: Optional[str] = None,
    add_to_yaml: bool = True,
    probe: bool = True,
    settings: Optional[dict] = None,
) -> dict:
    if probe:
        user_agent = (settings or {}).get("user_agent", "JobOpeningMonitor/1.0")
        detection = probe_careers_url(url, company_name=company_name, user_agent=user_agent)
    else:
        detection = detect_ats(url, company_name=company_name)
        if detection is None:
            from src.discovery.ats_detect_url import AtsDetection

            detection = AtsDetection(
                ats_type="career_portal",
                company_name=company_name or "Unknown",
                source={"type": "career_portal", "url": url},
                careers_url=url,
                confidence="low",
            )

    added = False
    if add_to_yaml:
        added = add_company_to_yaml(detection)

    company = upsert_company_db(db, detection)
    return {
        **detection.to_dict(),
        "added_to_yaml": added,
        "company_id": company.id,
    }


def import_company_pack(pack_name: str, *, merge: bool = True) -> dict:
    pack_path = PACKS_DIR / pack_name
    if not pack_path.exists():
        raise FileNotFoundError(f"Pack not found: {pack_path}")
    summary = import_pack_yaml(pack_path, merge=merge)
    return {"pack": pack_name, **summary}

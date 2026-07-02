"""Persist discovered companies to companies.yaml and Postgres."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from src.config import ROOT
from src.db.models import Company
from src.discovery.ats_detect_url import AtsDetection

logger = logging.getLogger(__name__)
COMPANIES_PATH = ROOT / "companies.yaml"


def _load_companies_file() -> dict:
    if not COMPANIES_PATH.exists():
        return {"companies": []}
    with COMPANIES_PATH.open() as f:
        return yaml.safe_load(f) or {"companies": []}


def _save_companies_file(data: dict) -> None:
    with COMPANIES_PATH.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _source_key(source: dict) -> str:
    stype = source.get("type", "")
    if stype in ("greenhouse", "lever", "ashby", "smartrecruiters"):
        return f"{stype}:{source.get('slug', '')}"
    if stype == "workday":
        return f"workday:{source.get('tenant')}:{source.get('site')}"
    if stype == "oracle":
        return f"oracle:{source.get('host')}:{source.get('site')}"
    if stype == "career_portal":
        return f"career_portal:{source.get('url', '')}"
    return str(source)


def add_company_to_yaml(detection: AtsDetection, *, replace: bool = False) -> bool:
    """Add company to companies.yaml. Returns True if added or updated."""
    data = _load_companies_file()
    companies = data.setdefault("companies", [])
    name = detection.company_name

    existing = next((c for c in companies if c.get("name", "").lower() == name.lower()), None)
    if existing is None:
        companies.append({"name": name, "sources": [detection.source]})
        _save_companies_file(data)
        logger.info("Added company %s to companies.yaml", name)
        return True

    sources = existing.setdefault("sources", [])
    new_key = _source_key(detection.source)
    if any(_source_key(s) == new_key for s in sources):
        return False

    if replace:
        sources[:] = [detection.source]
    else:
        sources.append(detection.source)
    _save_companies_file(data)
    logger.info("Updated company %s in companies.yaml", name)
    return True


def upsert_company_db(db: Session, detection: AtsDetection) -> Company:
    company = db.query(Company).filter(Company.name == detection.company_name).one_or_none()
    source = detection.source
    ats_type = source.get("type", detection.ats_type)
    slug = source.get("slug", "")
    if company is None:
        company = Company(
            name=detection.company_name,
            ats_type=ats_type,
            slug=slug,
            careers_url=detection.careers_url,
        )
        db.add(company)
    else:
        if not company.ats_type:
            company.ats_type = ats_type
        if not company.slug and slug:
            company.slug = slug
        if not company.careers_url:
            company.careers_url = detection.careers_url
    db.commit()
    db.refresh(company)
    return company


def import_pack_yaml(pack_path: Path, *, merge: bool = True) -> dict:
    """Import companies from a pack YAML file into companies.yaml."""
    with pack_path.open() as f:
        pack = yaml.safe_load(f) or {}
    incoming = pack.get("companies", [])
    data = _load_companies_file()
    companies = data.setdefault("companies", [])
    by_name = {c.get("name", "").lower(): c for c in companies}

    added = 0
    updated = 0
    skipped = 0
    for entry in incoming:
        name = entry.get("name", "").strip()
        if not name:
            continue
        sources = entry.get("sources", [])
        if not sources:
            skipped += 1
            continue
        key = name.lower()
        if key not in by_name:
            companies.append({"name": name, "sources": sources})
            by_name[key] = companies[-1]
            added += 1
            continue
        if not merge:
            by_name[key]["sources"] = sources
            updated += 1
            continue
        existing_sources = by_name[key].setdefault("sources", [])
        existing_keys = {_source_key(s) for s in existing_sources}
        for source in sources:
            sk = _source_key(source)
            if sk in existing_keys:
                skipped += 1
                continue
            existing_sources.append(source)
            updated += 1

    _save_companies_file(data)
    return {"added": added, "updated": updated, "skipped": skipped, "total": len(companies)}

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps.auth import require_user

from api.schemas.companies import (
    DiscoverRequest,
    DiscoverResponse,
    ImportPackRequest,
    ImportPackResponse,
)
from api.schemas.jobs import CompanyOut
from api.services.discovery import discover_company, import_company_pack
from src.config import ROOT, load_settings
from src.db import get_db
from src.db.models import Company, User

router = APIRouter(prefix="/companies", tags=["companies"])
PACKS_DIR = ROOT / "data" / "company_packs"


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)) -> list[CompanyOut]:
    return db.query(Company).order_by(Company.name).all()


@router.post("/discover", response_model=DiscoverResponse)
def discover_company_endpoint(
    body: DiscoverRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> DiscoverResponse:
    settings = load_settings()
    try:
        result = discover_company(
            db,
            body.url,
            company_name=body.company_name,
            add_to_yaml=body.add_to_yaml,
            probe=body.probe,
            settings=settings,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DiscoverResponse(**result)


@router.post("/import-pack", response_model=ImportPackResponse)
def import_pack_endpoint(
    body: ImportPackRequest,
    user: User = Depends(require_user),
) -> ImportPackResponse:
    try:
        result = import_company_pack(body.pack, merge=body.merge)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ImportPackResponse(**result)


@router.get("/packs", response_model=list[str])
def list_packs() -> list[str]:
    if not PACKS_DIR.is_dir():
        return []
    return sorted(p.name for p in PACKS_DIR.glob("*.yaml"))

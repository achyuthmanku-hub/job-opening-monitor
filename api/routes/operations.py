from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.schemas.jobs import AlertResponse, ParseResponse
from api.services.alerts import run_alerts
from api.services.nlp_pipeline import parse_jobs
from src.config import load_settings
from src.db import get_db

router = APIRouter(tags=["operations"])


@router.post("/alerts/run", response_model=AlertResponse)
def trigger_alerts(
    dry_run: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> AlertResponse:
    settings = load_settings()
    result = run_alerts(db, settings, dry_run=dry_run)
    return AlertResponse(**result)


@router.post("/parse", response_model=ParseResponse)
def trigger_parse(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> ParseResponse:
    result = parse_jobs(db, limit=limit)
    return ParseResponse(**result)

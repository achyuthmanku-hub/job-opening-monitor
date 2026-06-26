from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.schemas.jobs import CompanyOut, HealthResponse, ProfileCreate, ProfileOut
from src.db import get_database_url, get_db
from src.db.models import Company, Profile

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database_url=get_database_url())


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)) -> list[CompanyOut]:
    return db.query(Company).order_by(Company.name).all()


@router.post("/profiles", response_model=ProfileOut)
def create_profile(body: ProfileCreate, db: Session = Depends(get_db)) -> ProfileOut:
    profile = Profile(
        name=body.name,
        resume_text=body.resume_text,
        preferences_json=body.preferences_json,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

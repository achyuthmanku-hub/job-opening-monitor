from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database_url: str


class ScanRequest(BaseModel):
    store_all: bool = False
    enrich_descriptions: bool = True
    parse_nlp: bool = True
    description_limit: int = Field(default=50, ge=1, le=500)
    parse_limit: int = Field(default=100, ge=1, le=1000)


class ScanResponse(BaseModel):
    fetched: int
    stored: int
    created: int
    updated: int
    descriptions_enriched: int = 0
    jobs_parsed: int = 0


class CompanyOut(BaseModel):
    id: int
    name: str
    ats_type: str
    slug: str
    careers_url: str

    model_config = {"from_attributes": True}


class JobParsedOut(BaseModel):
    skills: list[str]
    seniority: str
    min_years: Optional[int]
    max_years: Optional[int]
    requires_clearance: bool
    sponsorship_mentioned: bool
    parsed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: int
    job_key: str
    company: str
    title: str
    url: str
    location: str
    source: str
    posted_at: str
    description_preview: str
    is_seen: bool
    parsed: Optional[JobParsedOut] = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    total: int
    jobs: list[JobOut]


class AlertResponse(BaseModel):
    new_jobs: int
    emailed: int
    dry_run: bool = False
    titles: list[str] = Field(default_factory=list)


class ParseResponse(BaseModel):
    parsed: int
    skipped: int


class ProfileCreate(BaseModel):
    name: str
    resume_text: str
    preferences_json: str = "{}"


class ProfileOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}

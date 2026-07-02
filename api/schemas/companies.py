from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DiscoverRequest(BaseModel):
    url: str
    company_name: Optional[str] = None
    add_to_yaml: bool = True
    probe: bool = True


class DiscoverResponse(BaseModel):
    ats_type: str
    company_name: str
    source: dict
    careers_url: str
    confidence: str
    added_to_yaml: bool
    company_id: Optional[int] = None


class ImportPackRequest(BaseModel):
    pack: str = Field(description="Pack filename under data/company_packs/, e.g. us_tech.yaml")
    merge: bool = True


class ImportPackResponse(BaseModel):
    pack: str
    added: int
    updated: int
    skipped: int
    total: int


class TaskEnqueueResponse(BaseModel):
    task_id: str
    task_name: str


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    ready: bool
    result: Optional[dict] = None

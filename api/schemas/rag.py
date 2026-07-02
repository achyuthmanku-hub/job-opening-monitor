from typing import Optional

from pydantic import BaseModel, Field


class EmbedResponse(BaseModel):
    profile_id: Optional[int] = None
    chunks: int = 0
    skipped: bool = False
    jobs_embedded: int = 0


class MatchItem(BaseModel):
    job_id: int
    company: str
    title: str
    url: str
    score: float
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class MatchListResponse(BaseModel):
    profile_id: int
    matched: int
    matches: list[MatchItem]


class MatchDetailResponse(MatchItem):
    profile_id: int

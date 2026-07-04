from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.schemas.auth import parse_preferences
from api.services.discovery import discover_company
from api.services.job_queries import query_jobs
from api.services.rag_pipeline import load_json_list, match_profile_to_jobs
from api.services.resume_onboarding import extract_resume_text, onboard_resume, read_upload
from src.config import ROOT, load_settings
from src.db import get_db
from src.db.models import Company, Job, JobMatch, Profile, User

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(ROOT / "api" / "templates"))


def _share_url(request: Request, profile_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/p/{profile_id}"


def _match_rows(db: Session, profile_id: int, min_score: float, limit: int = 50) -> list[dict]:
    rows = (
        db.query(JobMatch)
        .filter(JobMatch.profile_id == profile_id, JobMatch.score >= min_score)
        .options(joinedload(JobMatch.job).joinedload(Job.company))
        .order_by(JobMatch.score.desc())
        .limit(limit)
        .all()
    )
    matches = []
    for row in rows:
        job = row.job
        matches.append(
            {
                "score": round(row.score, 1),
                "company": job.company.name if job and job.company else "",
                "title": job.title if job else "",
                "url": job.url if job else "",
                "summary": row.summary or "",
                "strengths": load_json_list(row.strengths_json),
                "gaps": load_json_list(row.gaps_json),
            }
        )
    return matches


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db), error: str = Query(default="")) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "error": error,
            "job_count": db.query(func.count(Job.id)).scalar() or 0,
            "company_count": db.query(func.count(Company.id)).scalar() or 0,
            "profile_count": db.query(func.count(Profile.id)).scalar() or 0,
        },
    )


@router.post("/upload")
async def upload_resume(
    request: Request,
    name: str = Form(...),
    resume: UploadFile = File(...),
    use_llm: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        filename, data = await read_upload(resume)
        resume_text = extract_resume_text(filename, data)
        result = onboard_resume(
            db,
            name=name,
            resume_text=resume_text,
            min_score=40.0,
            limit=30,
            use_llm=bool(use_llm),
        )
        return RedirectResponse(url=f"/p/{result['profile_id']}", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/?error={quote(str(exc))}", status_code=303)


@router.get("/p/{profile_id}", response_class=HTMLResponse)
def profile_matches_page(
    request: Request,
    profile_id: int,
    min_score: float = Query(default=40.0, ge=0, le=100),
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    profile = db.query(Profile).filter(Profile.id == profile_id).one_or_none()
    if profile is None:
        return RedirectResponse(url="/?error=Profile%20not%20found", status_code=303)

    if refresh:
        match_profile_to_jobs(
            db,
            profile_id,
            min_score=0.0,
            limit=30,
            use_llm=False,
            store=True,
        )

    matches = _match_rows(db, profile_id, min_score=min_score)
    if not matches:
        # First visit with no stored matches — rank all jobs, keep top results.
        match_profile_to_jobs(
            db,
            profile_id,
            min_score=0.0,
            limit=30,
            use_llm=False,
            store=True,
        )
        matches = _match_rows(db, profile_id, min_score=min_score)

    return templates.TemplateResponse(
        request,
        "profile_matches.html",
        {
            "profile": profile,
            "matches": matches,
            "min_score": min_score,
            "share_url": _share_url(request, profile_id),
            "processing": False,
        },
    )


@router.get("/ui/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    job_count = db.query(func.count(Job.id)).scalar() or 0
    company_count = db.query(func.count(Company.id)).scalar() or 0
    profile_count = db.query(func.count(Profile.id)).scalar() or 0
    match_count = db.query(func.count(JobMatch.id)).scalar() or 0

    top_matches = (
        db.query(JobMatch)
        .options(joinedload(JobMatch.job).joinedload(Job.company))
        .order_by(JobMatch.score.desc())
        .limit(8)
        .all()
    )
    match_rows = []
    for match in top_matches:
        job = match.job
        match_rows.append(
            {
                "score": round(match.score, 1),
                "company": job.company.name if job and job.company else "",
                "title": job.title if job else "",
                "url": job.url if job else "",
                "summary": (match.summary or "")[:140],
            }
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "job_count": job_count,
            "company_count": company_count,
            "profile_count": profile_count,
            "match_count": match_count,
            "matches": match_rows,
        },
    )


@router.get("/ui/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    keyword: Optional[str] = None,
    company: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    total, jobs = query_jobs(db, limit=50, offset=0, keyword=keyword, company=company)
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {"jobs": jobs, "total": total, "keyword": keyword or "", "company": company or ""},
    )


@router.get("/ui/matches", response_class=HTMLResponse)
def matches_page(
    request: Request,
    profile_id: int = 1,
    min_score: float = 60,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    return RedirectResponse(url=f"/p/{profile_id}?min_score={min_score}", status_code=303)


@router.get("/ui/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    user = db.query(User).order_by(User.id).first()
    prefs = parse_preferences(user.preferences_json if user else "{}")
    settings = load_settings()
    alerts = settings.get("alerts", {})
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "user": user,
            "preferences": prefs,
            "alerts": alerts,
            "auth_enabled": settings.get("api_auth_enabled", False),
        },
    )


@router.get("/ui/discover", response_class=HTMLResponse)
def discover_page(
    request: Request,
    message: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "discover.html",
        {"message": message, "error": error},
    )


@router.post("/ui/discover")
def discover_submit(
    request: Request,
    url: str = Form(...),
    company_name: str = Form(default=""),
    add_to_yaml: bool = Form(default=True),
    db: Session = Depends(get_db),
):
    settings = load_settings()
    try:
        result = discover_company(
            db,
            url.strip(),
            company_name=company_name.strip() or None,
            add_to_yaml=add_to_yaml,
            probe=True,
            settings=settings,
        )
        message = (
            f"Detected {result['ats_type']} ({result['confidence']}) for "
            f"{result['company_name']}"
            + (" — added to companies.yaml" if result["added_to_yaml"] else "")
        )
        return RedirectResponse(url=f"/ui/discover?message={quote(message)}", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/ui/discover?error={quote(str(exc))}", status_code=303)

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from api.schemas.auth import parse_preferences
from src.db.models import Job, JobMatch, Profile, SeenJob, User
from src.filters.preferences import job_matches_preferences
from src.models import JobPosting
from src.notifier.channels import AlertJob, dispatch_alerts

logger = logging.getLogger(__name__)


def _to_posting(job: Job) -> JobPosting:
    return JobPosting(
        company=job.company.name if job.company else "",
        title=job.title,
        url=job.url,
        source=job.source,
        location=job.location,
        posted_at=job.posted_at,
    )


def _preferences_dict(user: Optional[User], profile: Optional[Profile]) -> dict:
    if profile and profile.preferences_json and profile.preferences_json.strip() not in ("", "{}"):
        try:
            return json.loads(profile.preferences_json)
        except json.JSONDecodeError:
            pass
    if user and user.id:
        return parse_preferences(user.preferences_json).model_dump()
    return {}


def get_new_jobs(
    db: Session,
    settings: dict,
    *,
    user: Optional[User] = None,
    profile: Optional[Profile] = None,
) -> list[Job]:
    preferences = _preferences_dict(user, profile)
    rows = (
        db.query(Job)
        .options(
            joinedload(Job.company),
            joinedload(Job.seen),
            joinedload(Job.parsed),
        )
        .all()
    )
    new_jobs: list[Job] = []
    for job in rows:
        if job.seen is not None:
            continue
        posting = _to_posting(job)
        parsed = job.parsed
        if not job_matches_preferences(
            posting,
            settings,
            preferences,
            sponsorship_mentioned=bool(parsed and parsed.sponsorship_mentioned),
            requires_clearance=bool(parsed and parsed.requires_clearance),
        ):
            continue
        new_jobs.append(job)
    return new_jobs


def _match_for_job(db: Session, profile_id: int, job_id: int) -> Optional[JobMatch]:
    return (
        db.query(JobMatch)
        .filter(JobMatch.profile_id == profile_id, JobMatch.job_id == job_id)
        .one_or_none()
    )


def _build_alert_jobs(
    db: Session,
    jobs: list[Job],
    *,
    profile_id: Optional[int],
    min_match_score: float,
    include_scores: bool,
) -> list[AlertJob]:
    alert_jobs: list[AlertJob] = []
    for job in jobs:
        posting = _to_posting(job)
        match_score = None
        summary = ""
        strengths: list[str] = []
        gaps: list[str] = []
        if include_scores and profile_id:
            match = _match_for_job(db, profile_id, job.id)
            if match:
                match_score = match.score
                summary = match.summary or ""
                try:
                    strengths = json.loads(match.strengths_json or "[]")
                    gaps = json.loads(match.gaps_json or "[]")
                except json.JSONDecodeError:
                    pass
                if match_score < min_match_score:
                    continue
        alert_jobs.append(
            AlertJob(
                posting=posting,
                match_score=match_score,
                match_summary=summary,
                strengths=strengths,
                gaps=gaps,
            )
        )
    return alert_jobs


def run_alerts(
    db: Session,
    settings: dict,
    *,
    dry_run: bool = False,
    user: Optional[User] = None,
) -> dict:
    alerts_cfg = settings.get("alerts", {})
    profile_id = alerts_cfg.get("profile_id")
    profile = None
    if profile_id:
        profile = db.query(Profile).filter(Profile.id == profile_id).one_or_none()

    preferences = _preferences_dict(user, profile)
    min_match_score = float(
        preferences.get("min_match_score", alerts_cfg.get("min_match_score", 0))
    )
    include_scores = bool(alerts_cfg.get("include_match_scores", True) and profile_id)

    new_jobs = get_new_jobs(db, settings, user=user, profile=profile)
    if not new_jobs:
        return {"new_jobs": 0, "notified": 0, "channels": {}}

    alert_jobs = _build_alert_jobs(
        db,
        new_jobs,
        profile_id=profile_id,
        min_match_score=min_match_score,
        include_scores=include_scores,
    )
    if not alert_jobs:
        return {
            "new_jobs": len(new_jobs),
            "notified": 0,
            "channels": {},
            "filtered_by_match_score": True,
        }

    if dry_run:
        return {
            "new_jobs": len(alert_jobs),
            "notified": 0,
            "dry_run": True,
            "titles": [
                f"{item.posting.company} — {item.posting.title}"
                + (f" ({item.match_score:.0f}%)" if item.match_score else "")
                for item in alert_jobs[:20]
            ],
        }

    channels_cfg = alerts_cfg.get("channels", {})
    user_channels = preferences.get("alert_channels", {})
    channels = {
        "email": user_channels.get("email", channels_cfg.get("email", True)),
        "slack": user_channels.get("slack", channels_cfg.get("slack", False)),
        "discord": user_channels.get("discord", channels_cfg.get("discord", False)),
        "telegram": user_channels.get("telegram", channels_cfg.get("telegram", False)),
    }

    sent = dispatch_alerts(
        alert_jobs,
        smtp_config=settings["smtp"],
        channels=channels,
        slack_webhook=os.getenv("SLACK_WEBHOOK_URL", "").strip(),
        discord_webhook=os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    )

    now = datetime.now(timezone.utc)
    for job in new_jobs:
        seen = job.seen
        if seen is None:
            seen = SeenJob(job_id=job.id)
            db.add(seen)
        seen.notified_at = now
    db.commit()

    notified = max(sent.values()) if sent else 0
    logger.info("Alerts sent for %d job(s) via %s", len(alert_jobs), sent)
    return {"new_jobs": len(alert_jobs), "notified": notified, "channels": sent}

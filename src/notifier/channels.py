"""Multi-channel job alert delivery."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

from src.models import JobPosting
from src.notifier import send_email

logger = logging.getLogger(__name__)


@dataclass
class AlertJob:
    posting: JobPosting
    match_score: Optional[float] = None
    match_summary: str = ""
    strengths: list = field(default_factory=list)
    gaps: list = field(default_factory=list)


def _format_job_line(alert_job: AlertJob) -> str:
    job = alert_job.posting
    location = f" — {job.location}" if job.location else ""
    score = ""
    if alert_job.match_score is not None:
        score = f" ({alert_job.match_score:.0f}% fit)"
    lines = [f"• {job.company}: {job.title}{location}{score}", f"  {job.url}"]
    if alert_job.match_summary:
        lines.append(f"  Why: {alert_job.match_summary[:200]}")
    if alert_job.gaps:
        lines.append(f"  Gap: {', '.join(alert_job.gaps[:5])}")
    return "\n".join(lines)


def format_alert_body(alert_jobs: list[AlertJob]) -> str:
    header = f"New job postings detected ({len(alert_jobs)}):\n\n"
    return header + "\n\n".join(_format_job_line(item) for item in alert_jobs)


def send_slack_alert(alert_jobs: list[AlertJob], webhook_url: str) -> None:
    if not alert_jobs or not webhook_url:
        return
    text = format_alert_body(alert_jobs)
    payload = {"text": text[:3900]}
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    logger.info("Slack alert sent for %d job(s).", len(alert_jobs))


def send_discord_alert(alert_jobs: list[AlertJob], webhook_url: str) -> None:
    if not alert_jobs or not webhook_url:
        return
    description = format_alert_body(alert_jobs)[:3900]
    payload = {
        "embeds": [
            {
                "title": f"New job openings ({len(alert_jobs)})",
                "description": description,
                "color": 5814783,
            }
        ]
    }
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    logger.info("Discord alert sent for %d job(s).", len(alert_jobs))


def send_telegram_alert(
    alert_jobs: list[AlertJob],
    *,
    bot_token: str,
    chat_id: str,
) -> None:
    if not alert_jobs or not bot_token or not chat_id:
        return
    text = format_alert_body(alert_jobs)[:3900]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()
    logger.info("Telegram alert sent for %d job(s).", len(alert_jobs))


def dispatch_alerts(
    alert_jobs: list[AlertJob],
    *,
    smtp_config: dict,
    channels: dict,
    slack_webhook: str = "",
    discord_webhook: str = "",
    telegram_bot_token: str = "",
    telegram_chat_id: str = "",
) -> dict[str, int]:
    """Send alerts on enabled channels. Returns per-channel job counts."""
    sent: dict[str, int] = {}
    if not alert_jobs:
        return sent

    if channels.get("email", True):
        postings = [item.posting for item in alert_jobs]
        send_email(postings, smtp_config)
        sent["email"] = len(alert_jobs)

    if channels.get("slack") and slack_webhook:
        send_slack_alert(alert_jobs, slack_webhook)
        sent["slack"] = len(alert_jobs)

    if channels.get("discord") and discord_webhook:
        send_discord_alert(alert_jobs, discord_webhook)
        sent["discord"] = len(alert_jobs)

    if channels.get("telegram") and telegram_bot_token and telegram_chat_id:
        send_telegram_alert(
            alert_jobs,
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
        )
        sent["telegram"] = len(alert_jobs)

    return sent

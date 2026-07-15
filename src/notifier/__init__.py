import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from ..models import JobPosting


def send_email(
    jobs: list[JobPosting],
    smtp_config: dict,
    *,
    digest: bool = False,
) -> None:
    if not jobs:
        return

    required = ("host", "port", "user", "password", "notify_email")
    missing = [key for key in required if not smtp_config.get(key)]
    if missing:
        raise ValueError(
            "Email notification is not configured. Set SMTP_* and NOTIFY_EMAIL in .env"
        )

    subject = (
        f"Daily job digest ({len(jobs)} openings, 1–5 yrs)"
        if digest
        else f"New job openings ({len(jobs)})"
    )
    lines = []
    for job in jobs:
        location = f" — {job.location}" if job.location else ""
        lines.append(
            f"• {job.company}: {job.title}{location}\n"
            f"  Source: {job.source}\n"
            f"  {job.url}\n"
        )

    body = (
        "Daily digest — new SWE / backend roles (US, ~1–5 years experience):\n\n"
        if digest
        else "New job postings detected:\n\n"
    ) + "\n".join(lines)

    msg = MIMEMultipart()
    msg["From"] = smtp_config["user"]
    msg["To"] = smtp_config["notify_email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)


def send_application_email(
    *,
    company: str,
    title: str,
    url: str,
    match_score: float,
    resume_path: Path,
    smtp_config: dict,
    status: str,
) -> None:
    required = ("host", "port", "user", "password", "notify_email")
    missing = [key for key in required if not smtp_config.get(key)]
    if missing:
        raise ValueError(
            "Email notification is not configured. Set SMTP_* and NOTIFY_EMAIL in .env"
        )

    subject = f"Job application ready: {company} — {title} ({match_score:.0f}% match)"
    body = (
        f"Application package prepared.\n\n"
        f"Company: {company}\n"
        f"Role: {title}\n"
        f"Match score: {match_score:.1f}%\n"
        f"Status: {status}\n"
        f"Apply here: {url}\n\n"
        f"Tailored ATS resume attached."
    )

    msg = MIMEMultipart()
    msg["From"] = smtp_config["user"]
    msg["To"] = smtp_config["notify_email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    attachment = MIMEApplication(resume_path.read_bytes(), _subtype="docx")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=resume_path.name,
    )
    msg.attach(attachment)

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)

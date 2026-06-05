import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .models import JobPosting


def send_email(jobs: list[JobPosting], smtp_config: dict) -> None:
    if not jobs:
        return

    required = ("host", "port", "user", "password", "notify_email")
    missing = [key for key in required if not smtp_config.get(key)]
    if missing:
        raise ValueError(
            "Email notification is not configured. Set SMTP_* and NOTIFY_EMAIL in .env"
        )

    subject = f"New job openings ({len(jobs)})"
    lines = []
    for job in jobs:
        location = f" — {job.location}" if job.location else ""
        lines.append(
            f"• {job.company}: {job.title}{location}\n"
            f"  Source: {job.source}\n"
            f"  {job.url}\n"
        )

    body = "New job postings detected:\n\n" + "\n".join(lines)

    msg = MIMEMultipart()
    msg["From"] = smtp_config["user"]
    msg["To"] = smtp_config["notify_email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)

import re

import requests

CLOSED_MARKERS = (
    "no longer available",
    "position has been filled",
    "job is closed",
    "posting is closed",
    "this job has expired",
    "page not found",
    "404",
    "job not found",
    "no open positions",
)


def check_role_status(url: str, settings: dict) -> str:
    try:
        response = requests.get(
            url,
            timeout=settings["request_timeout"],
            headers={"User-Agent": settings["user_agent"]},
            allow_redirects=True,
        )
        if response.status_code in (404, 410):
            return "closed"
        if response.status_code >= 500:
            return "unknown"

        text = re.sub(r"\s+", " ", response.text.lower())
        if any(marker in text for marker in CLOSED_MARKERS):
            return "closed"
        return "open"
    except Exception:
        return "unknown"

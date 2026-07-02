"""Per-host HTTP rate limiting with retries for scrapers."""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_lock = Lock()
_last_request: dict[str, float] = {}


def _host_from_url(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _rate_limit_config(settings: dict) -> tuple[float, int, float]:
    cfg = settings.get("rate_limit", {})
    rps = float(cfg.get("requests_per_second", 1.0))
    max_retries = int(cfg.get("max_retries", 3))
    backoff = float(cfg.get("backoff_seconds", 1.5))
    return max(rps, 0.1), max_retries, backoff


def _wait_for_slot(host: str, min_interval: float) -> None:
    with _lock:
        now = time.monotonic()
        last = _last_request.get(host, 0.0)
        wait = min_interval - (now - last)
        if wait > 0:
            time.sleep(wait)
        _last_request[host] = time.monotonic()


def _default_headers(settings: dict) -> dict[str, str]:
    return {"User-Agent": settings.get("user_agent", "JobOpeningMonitor/1.0")}


def http_get(
    url: str,
    settings: dict,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> requests.Response:
    rps, max_retries, backoff = _rate_limit_config(settings)
    min_interval = 1.0 / rps
    host = _host_from_url(url)
    merged_headers = _default_headers(settings)
    if headers:
        merged_headers.update(headers)
    if timeout is None:
        timeout = settings.get("request_timeout", 30)

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        _wait_for_slot(host, min_interval)
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers=merged_headers,
                **kwargs,
            )
            if response.status_code in (429, 503) and attempt < max_retries:
                sleep_for = backoff * (2**attempt)
                logger.warning(
                    "HTTP %d from %s — retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    host,
                    sleep_for,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(sleep_for)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            sleep_for = backoff * (2**attempt)
            logger.warning(
                "Request failed for %s — retrying in %.1fs: %s",
                host,
                sleep_for,
                exc,
            )
            time.sleep(sleep_for)
    raise last_error or requests.RequestException(f"GET {url} failed")


def http_post(
    url: str,
    settings: dict,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> requests.Response:
    rps, max_retries, backoff = _rate_limit_config(settings)
    min_interval = 1.0 / rps
    host = _host_from_url(url)
    merged_headers = _default_headers(settings)
    if headers:
        merged_headers.update(headers)
    if timeout is None:
        timeout = settings.get("request_timeout", 30)

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        _wait_for_slot(host, min_interval)
        try:
            response = requests.post(
                url,
                timeout=timeout,
                headers=merged_headers,
                **kwargs,
            )
            if response.status_code in (429, 503) and attempt < max_retries:
                time.sleep(backoff * (2**attempt))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(backoff * (2**attempt))
    raise last_error or requests.RequestException(f"POST {url} failed")

"""Scraper plugin registry."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

ScraperFn = Callable[..., list]

SCRAPERS: dict[str, ScraperFn] = {}


def register_scraper(name: str, fn: ScraperFn) -> ScraperFn:
    SCRAPERS[name] = fn
    return fn


def load_plugins() -> None:
    """Load optional scraper plugins from src/scrapers/plugins/*.py."""
    plugins_dir = Path(__file__).resolve().parent / "plugins"
    if not plugins_dir.is_dir():
        return
    for path in sorted(plugins_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"src.scrapers.plugins.{path.stem}"
        try:
            importlib.import_module(module_name)
            logger.debug("Loaded scraper plugin %s", module_name)
        except Exception:
            logger.exception("Failed to load scraper plugin %s", module_name)

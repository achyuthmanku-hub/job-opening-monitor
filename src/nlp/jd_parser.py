import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from src.config import ROOT

SENIORITY_PATTERNS = [
    (re.compile(r"\b(intern|internship)\b", re.I), "intern"),
    (re.compile(r"\b(entry[- ]?level|new grad|graduate)\b", re.I), "junior"),
    (re.compile(r"\b(junior|jr\.?)\b", re.I), "junior"),
    (re.compile(r"\b(senior|sr\.?|staff|principal|lead|director|architect)\b", re.I), "senior"),
    (re.compile(r"\bsoftware engineer ii\b", re.I), "mid"),
    (re.compile(r"\bsoftware engineer i\b", re.I), "junior"),
]

YEARS_PATTERN = re.compile(
    r"(\d+)\s*\+?\s*(?:to|-)?\s*(\d+)?\s*years?",
    re.I,
)

CLEARANCE_PATTERN = re.compile(
    r"\b(clearance|ts/sci|secret clearance|security clearance|top secret)\b",
    re.I,
)

SPONSORSHIP_PATTERN = re.compile(
    r"\b(sponsorship|visa|h-?1b|work authorization|authorized to work)\b",
    re.I,
)


@dataclass
class ParsedJobDescription:
    skills: list[str]
    seniority: str
    min_years: Optional[int]
    max_years: Optional[int]
    requires_clearance: bool
    sponsorship_mentioned: bool


@lru_cache
def load_skill_ontology() -> dict[str, list[str]]:
    path = ROOT / "data" / "skills_ontology.yaml"
    if not path.exists():
        return {}
    with path.open() as handle:
        data = yaml.safe_load(handle) or {}
    return {str(k).lower(): [str(v).lower() for v in values] for k, values in data.items()}


def extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for canonical, aliases in load_skill_ontology().items():
        for alias in aliases:
            if alias in lower and canonical not in found:
                found.append(canonical)
                break
    return sorted(found)


def extract_seniority(title: str, description: str = "") -> str:
    combined = f"{title} {description}"
    for pattern, label in SENIORITY_PATTERNS:
        if pattern.search(combined):
            return label
    if re.search(r"\bsoftware engineer\b", title, re.I):
        return "mid"
    return "unknown"


def extract_years_range(title: str, description: str) -> tuple[Optional[int], Optional[int]]:
    combined = f"{title}\n{description}"
    min_years: Optional[int] = None
    max_years: Optional[int] = None
    for match in YEARS_PATTERN.finditer(combined):
        first = int(match.group(1))
        second = int(match.group(2)) if match.group(2) else None
        if second is not None:
            min_years = first if min_years is None else min(min_years, first)
            max_years = second if max_years is None else max(max_years, second)
        else:
            min_years = first if min_years is None else min(min_years, first)
            max_years = first if max_years is None else max(max_years, first)
    return min_years, max_years


def parse_job_description(title: str, description: str = "") -> ParsedJobDescription:
    text = f"{title}\n{description}".strip()
    min_years, max_years = extract_years_range(title, description)
    return ParsedJobDescription(
        skills=extract_skills(text),
        seniority=extract_seniority(title, description),
        min_years=min_years,
        max_years=max_years,
        requires_clearance=bool(CLEARANCE_PATTERN.search(text)),
        sponsorship_mentioned=bool(SPONSORSHIP_PATTERN.search(text)),
    )


def parsed_to_json(parsed: ParsedJobDescription) -> str:
    return json.dumps(parsed.skills)

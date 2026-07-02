from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    name: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    user: UserOut
    api_key: str


class ApiKeyCreateRequest(BaseModel):
    label: str = "default"


class ApiKeyCreateResponse(BaseModel):
    id: int
    label: str
    key_prefix: str
    api_key: str


class AlertChannels(BaseModel):
    email: bool = True
    slack: bool = False
    discord: bool = False
    telegram: bool = False


class UserPreferences(BaseModel):
    countries: list[str] = Field(default_factory=lambda: ["US"])
    work_authorization: str = "any"  # any | h1b_ok | no_sponsorship_needed
    skip_clearance: bool = True
    min_match_score: float = 70.0
    keywords: list[str] = Field(default_factory=list)
    alert_channels: AlertChannels = Field(default_factory=AlertChannels)


class PreferencesUpdate(BaseModel):
    countries: Optional[list[str]] = None
    work_authorization: Optional[str] = None
    skip_clearance: Optional[bool] = None
    min_match_score: Optional[float] = None
    keywords: Optional[list[str]] = None
    alert_channels: Optional[AlertChannels] = None


class PreferencesResponse(BaseModel):
    user_id: int
    preferences: UserPreferences


def parse_preferences(raw: str) -> UserPreferences:
    if not raw or raw.strip() in ("", "{}"):
        return UserPreferences()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return UserPreferences()
        return UserPreferences(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return UserPreferences()


def dump_preferences(prefs: UserPreferences) -> str:
    return json.dumps(prefs.model_dump(), separators=(",", ":"))


def merge_preferences(current: UserPreferences, update: PreferencesUpdate) -> UserPreferences:
    data = current.model_dump()
    patch = update.model_dump(exclude_unset=True)
    if "alert_channels" in patch and patch["alert_channels"] is not None:
        channels = data.get("alert_channels", {})
        channels.update(patch.pop("alert_channels"))
        data["alert_channels"] = channels
    data.update(patch)
    return UserPreferences(**data)

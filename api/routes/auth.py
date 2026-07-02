from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import auth_enabled, create_api_key, create_user
from api.deps.auth import require_user
from api.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    PreferencesResponse,
    PreferencesUpdate,
    RegisterRequest,
    RegisterResponse,
    UserOut,
    dump_preferences,
    merge_preferences,
    parse_preferences,
)
from src.db import get_db
from src.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse)
def register_user(body: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing_count = db.query(User).count()
    bootstrap_secret = os.getenv("BOOTSTRAP_SECRET", "").strip()
    if existing_count > 0 and not bootstrap_secret:
        raise HTTPException(
            status_code=403,
            detail="Registration closed. Set BOOTSTRAP_SECRET to create additional users.",
        )

    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = create_user(db, email=email, name=body.name)
    _, raw_key = create_api_key(db, user, label="default")
    return RegisterResponse(user=UserOut.model_validate(user), api_key=raw_key)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(require_user)) -> UserOut:
    if user.id == 0:
        return UserOut(id=0, email="local@dev", name="Local Dev")
    return UserOut.model_validate(user)


@router.get("/me/preferences", response_model=PreferencesResponse)
def get_preferences(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PreferencesResponse:
    if user.id == 0:
        return PreferencesResponse(user_id=0, preferences=parse_preferences("{}"))
    db_user = db.query(User).filter(User.id == user.id).one()
    return PreferencesResponse(
        user_id=db_user.id,
        preferences=parse_preferences(db_user.preferences_json),
    )


@router.patch("/me/preferences", response_model=PreferencesResponse)
def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PreferencesResponse:
    if user.id == 0:
        raise HTTPException(status_code=400, detail="Auth disabled; preferences are read-only in local mode.")
    db_user = db.query(User).filter(User.id == user.id).one()
    current = parse_preferences(db_user.preferences_json)
    merged = merge_preferences(current, body)
    db_user.preferences_json = dump_preferences(merged)
    db.commit()
    db.refresh(db_user)
    return PreferencesResponse(user_id=db_user.id, preferences=merged)


@router.post("/keys", response_model=ApiKeyCreateResponse)
def create_key(
    body: ApiKeyCreateRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    if user.id == 0:
        raise HTTPException(status_code=400, detail="Enable API_AUTH_ENABLED to manage API keys.")
    db_user = db.query(User).filter(User.id == user.id).one()
    row, raw_key = create_api_key(db, db_user, label=body.label)
    return ApiKeyCreateResponse(
        id=row.id,
        label=row.label,
        key_prefix=row.key_prefix,
        api_key=raw_key,
    )

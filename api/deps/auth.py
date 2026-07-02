from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import auth_enabled, extract_api_key, verify_api_key
from src.db import get_db
from src.db.models import User


def get_current_user_optional(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Optional[User]:
    if not auth_enabled():
        return None
    raw_key = extract_api_key(authorization, x_api_key)
    return verify_api_key(db, raw_key)


def require_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if not auth_enabled():
        return User(id=0, email="local@dev", name="Local Dev")
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Pass X-API-Key or Authorization: Bearer.",
        )
    return user

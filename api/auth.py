"""API key generation and verification."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.db.models import ApiKey, User

KEY_PREFIX = "jim_"


def auth_enabled() -> bool:
    return os.getenv("API_AUTH_ENABLED", "false").strip().lower() in ("1", "true", "yes")


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> Tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash)."""
    token = secrets.token_urlsafe(32)
    raw_key = f"{KEY_PREFIX}{token}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:12]
    return raw_key, key_prefix, key_hash


def extract_api_key(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def verify_api_key(db: Session, raw_key: Optional[str]) -> Optional[User]:
    if not raw_key:
        return None
    key_hash = hash_api_key(raw_key)
    row = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).one_or_none()
    if row is None:
        return None
    row.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return row.user


def create_user(db: Session, *, email: str, name: str) -> User:
    user = User(email=email.strip().lower(), name=name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_api_key(db: Session, user: User, *, label: str = "default") -> Tuple[ApiKey, str]:
    raw_key, key_prefix, key_hash = generate_api_key()
    row = ApiKey(user_id=user.id, label=label, key_prefix=key_prefix, key_hash=key_hash)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, raw_key

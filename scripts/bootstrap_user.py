#!/usr/bin/env python3
"""Create the first platform user and API key."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.auth import create_api_key, create_user  # noqa: E402
from api.schemas.auth import UserPreferences, dump_preferences  # noqa: E402
from src.db import SessionLocal  # noqa: E402
from src.db.models import Profile, User  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a user and API key")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--link-profile", type=int, default=1, help="Attach profile id to user")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        existing = db.query(User).filter(User.email == email).one_or_none()
        if existing:
            print(f"User already exists: {existing.email} (id={existing.id})", file=sys.stderr)
            return 1

        prefs = UserPreferences()
        user = create_user(db, email=email, name=args.name)
        user.preferences_json = dump_preferences(prefs)
        db.commit()

        _, raw_key = create_api_key(db, user, label="bootstrap")

        profile = db.query(Profile).filter(Profile.id == args.link_profile).one_or_none()
        if profile and profile.user_id is None:
            profile.user_id = user.id
            db.commit()
            print(f"Linked profile {profile.id} to user {user.id}")

        print("User created successfully.")
        print(f"  id:    {user.id}")
        print(f"  email: {user.email}")
        print(f"  name:  {user.name}")
        print(f"  API key (save now — shown once):\n  {raw_key}")
        print("\nEnable auth with API_AUTH_ENABLED=true in .env")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

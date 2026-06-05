#!/usr/bin/env python3
"""Test Gmail SMTP configuration. Run: python scripts/test_email.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.models import JobPosting
from src.notifier import send_email


def main() -> int:
    try:
        settings = load_settings()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    smtp = settings["smtp"]
    print("SMTP user:", smtp["user"] or "(not set)")
    print("Password length:", len(smtp["password"]), "(must be 16 for Gmail)")

    if not smtp["user"] or "your-email" in smtp["user"]:
        print("\nERROR: Edit .env and set your real Gmail address in SMTP_USER")
        return 1
    if len(smtp["password"]) != 16:
        print("\nERROR: Gmail app password must be exactly 16 characters (no spaces)")
        return 1

    try:
        send_email(
            [JobPosting("Test", "Software Engineer", "https://example.com", "test")],
            smtp,
        )
        print("\nSUCCESS: Test email sent to", smtp["notify_email"])
        return 0
    except Exception as exc:
        print("\nFAILED:", exc)
        print("\nFix:")
        print("1. Enable 2-Step Verification: https://myaccount.google.com/security")
        print("2. Create NEW app password: https://myaccount.google.com/apppasswords")
        print("3. Paste 16-char password (no spaces) into .env as SMTP_PASSWORD")
        print("4. Save .env (Cmd+S in Cursor) then run this script again")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

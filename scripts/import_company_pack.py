#!/usr/bin/env python3
"""Import a company pack YAML into companies.yaml."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.discovery.company_store import import_pack_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import company pack into companies.yaml")
    parser.add_argument(
        "pack",
        help="Pack filename (e.g. us_tech.yaml) or path under data/company_packs/",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Replace sources for existing companies instead of merging",
    )
    args = parser.parse_args()

    pack_path = Path(args.pack)
    if not pack_path.is_absolute():
        candidate = ROOT / "data" / "company_packs" / pack_path.name
        pack_path = candidate if candidate.exists() else ROOT / pack_path

    if not pack_path.exists():
        print(f"Pack not found: {pack_path}", file=sys.stderr)
        return 1

    summary = import_pack_yaml(pack_path, merge=not args.no_merge)
    print(
        f"Imported {pack_path.name}: "
        f"added={summary['added']} updated={summary['updated']} "
        f"skipped={summary['skipped']} total={summary['total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

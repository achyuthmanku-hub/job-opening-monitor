#!/usr/bin/env bash
# Daily 8:00 AM CST: job monitor only (email new postings).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"

cd "$PROJECT_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S %Z'): Morning monitor run started."

"$PYTHON_BIN" run.py

echo "$(date '+%Y-%m-%d %H:%M:%S %Z'): Morning monitor run finished."

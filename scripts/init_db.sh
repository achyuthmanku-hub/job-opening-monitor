#!/usr/bin/env bash
# Create tables via Alembic migrations.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p data
alembic upgrade head
echo "Database ready."

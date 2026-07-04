#!/usr/bin/env bash
# Production web entrypoint: config bootstrap, migrations, uvicorn.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f config.yaml ]; then
  echo "Creating config.yaml from config.example.yaml"
  cp config.example.yaml config.yaml
fi

if [ ! -f companies.yaml ]; then
  echo "Creating companies.yaml from companies.example.yaml"
  cp companies.example.yaml companies.yaml
  if [ "${IMPORT_FORTUNE500:-true}" = "true" ]; then
    echo "Importing Fortune 500 company pack..."
    python scripts/import_company_pack.py fortune500.yaml || true
  fi
fi

echo "Running database migrations..."
alembic upgrade head

PORT="${PORT:-8000}"
WORKERS="${WEB_WORKERS:-1}"
echo "Starting API on 0.0.0.0:${PORT} (workers=${WORKERS})"
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" --workers "${WORKERS}"

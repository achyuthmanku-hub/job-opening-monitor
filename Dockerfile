FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model so first resume upload is faster
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN chmod +x scripts/start_web.sh scripts/import_company_pack.py scripts/bootstrap_user.py

ENV PYTHONUNBUFFERED=1 \
    IMPORT_FORTUNE500=true \
    WEB_WORKERS=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD curl -f "http://127.0.0.1:${PORT:-8000}/health" || exit 1

CMD ["bash", "scripts/start_web.sh"]

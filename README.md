# Job Intelligence Monitor

A Python platform that watches company career portals and ATS boards, enriches jobs with NLP, matches them to your resume with RAG, and alerts you via email, Slack, Discord, or Telegram.

## Quick start (CLI monitor)

```bash
cd ~/job-opening-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp companies.example.yaml companies.yaml
cp .env.example .env
```

### Preview / seed / run

```bash
python run.py --dry-run
python run.py --seed
python run.py
```

## Platform API (Phases 1–5)

### 1. Database

```bash
createdb job_monitor   # or ./scripts/init_db.sh
alembic upgrade head
```

Set in `.env`:

```
DATABASE_URL=postgresql://localhost/job_monitor
REDIS_URL=redis://localhost:6379/0
```

### 2. Start services

```bash
# API + web UI
python run_api.py

# Background workers (optional)
celery -A api.celery_app worker -l info
celery -A api.celery_app beat -l info
```

Open:
- **Dashboard:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

### 3. Core workflow

```bash
# Scan jobs into Postgres
curl -X POST http://localhost:8000/jobs/scan

# View RAG matches
curl "http://localhost:8000/profiles/1/matches?min_score=70&refresh=true"

# Send smart alerts (email + optional Slack/Discord)
curl -X POST http://localhost:8000/alerts/run
```

### 4. Docker

```bash
docker compose up
```

## Architecture

```
Scrapers → Postgres (jobs) → NLP parser → RAG embeddings → Match scores
                ↓                                      ↓
         Company discovery                    Email / Slack / Discord / Telegram
```

| Phase | Feature |
|-------|---------|
| 1 | FastAPI + Postgres ingestion |
| 2 | NLP skill/seniority extraction |
| 3 | RAG resume–job matching |
| 4 | Celery workers, ATS discovery, company packs |
| 5 | Multi-user API keys, global filters, multi-channel alerts |

## Company discovery

```bash
# API
curl -X POST http://localhost:8000/companies/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "https://jobs.ashbyhq.com/ramp", "company_name": "Ramp"}'

# Import a pack (15+ companies)
python scripts/import_company_pack.py us_tech.yaml
```

Or use the web UI: http://localhost:8000/ui/discover

## Multi-user auth (Phase 5)

```bash
# Create first user + API key
python scripts/bootstrap_user.py --email you@example.com --name "Your Name"

# Enable in .env
API_AUTH_ENABLED=true
```

Pass `X-API-Key: jim_...` on write endpoints (`POST /jobs/scan`, `/companies/discover`, etc.).

Update preferences:

```bash
curl -X PATCH http://localhost:8000/auth/me/preferences \
  -H "X-API-Key: jim_..." \
  -H "Content-Type: application/json" \
  -d '{"countries":["US","CA"],"work_authorization":"h1b_ok","alert_channels":{"slack":true}}'
```

## Smart alerts

Configure in `config.yaml`:

```yaml
alerts:
  profile_id: 1
  min_match_score: 70
  include_match_scores: true
  channels:
    email: true
    slack: true
```

Set webhooks in `.env`:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Alert format includes RAG fit score when available:

```
Stripe — Backend Engineer (91% fit)
Why: Java/Spring + payments experience aligns
Gap: Go preferred
https://...
```

## Configure companies

Edit `companies.yaml`. Supported source types:

| Type | Example |
|------|---------|
| `greenhouse` | `slug: stripe` |
| `ashby` | `slug: notion` |
| `lever` | `slug: plaid` |
| `workday` | `tenant`, `wd`, `site` |
| `oracle` | `host`, `site` |
| `amazon` | optional `query` |
| `career_portal` | full careers URL |

## Email setup (Gmail)

1. Enable 2FA
2. Create an [App Password](https://myaccount.google.com/apppasswords)
3. Set in `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFY_EMAIL=you@gmail.com
```

## Filters (`config.yaml`)

```yaml
keywords:
  - "software engineer"

filters:
  us_only: true
  posted_min_hours: 1
  posted_max_hours: 25
  experience_max_years: 5
```

Per-user overrides via `PATCH /auth/me/preferences` (countries, work authorization, alert channels).

## Project layout

```
job-opening-monitor/
├── api/                    # FastAPI routes, services, Celery tasks
├── src/
│   ├── scrapers/           # ATS fetchers + rate limiting
│   ├── nlp/                # JD parser
│   ├── rag/                # Embeddings + matching
│   ├── discovery/          # ATS auto-detection
│   └── notifier/           # Email + Slack/Discord/Telegram
├── data/company_packs/     # Importable company lists
├── alembic/                # Postgres migrations
├── run.py                  # CLI monitor (SQLite)
├── run_api.py              # API server
└── docker-compose.yml
```

## Limitations

- LinkedIn, Indeed, and Glassdoor may block automated requests — prefer ATS APIs.
- First run emails all unseen jobs unless you seed the database.
- RAG matching uses OpenAI when `OPENAI_API_KEY` is set; falls back to vector-only otherwise.

# Job Intelligence Monitor

**AI-powered job intelligence platform** — ingest roles from major ATS boards, parse them with NLP, rank them against a resume with RAG, and deliver explainable alerts.

Built as a production-style backend system: FastAPI API, PostgreSQL, Celery workers, Redis, Docker, and a small web UI.

[Features](#features) · [Architecture](#architecture) · [Quick start](#quick-start) · [API](#platform-api) · [Tech stack](#tech-stack)

---

## For friends (multi-resume matching)

Jobs are scraped **once** into a shared pool. Each person uploads their own resume and gets a personal ranked list.

1. **You (operator):** import Fortune 500 pack → scan → embed jobs  
2. **Friends:** open the site → **Upload resume** → see matches  

```bash
python scripts/import_company_pack.py fortune500.yaml
# start API: python run_api.py
curl -X POST http://localhost:8000/jobs/scan
curl -X POST "http://localhost:8000/jobs/embed"
# Friends visit: http://localhost:8000/ui/upload
```

The Fortune 500 pack (`data/company_packs/fortune500.yaml`) covers **100+** major US employers with public ATS boards (not every F500 site is scrapeable).

---

## Why this exists

Job search across dozens of company career pages is noisy and manual. This project turns that into a **pipeline**:

1. **Ingest** jobs from Greenhouse, Ashby, Lever, Workday, Oracle, Amazon, and more  
2. **Filter** by role, location, posting window, and experience level  
3. **Enrich** with NLP (skills, seniority, years, clearance, sponsorship)  
4. **Match** resume ↔ job with embeddings + optional LLM scoring  
5. **Alert** on email, Slack, Discord, or Telegram with fit % and gaps  

It is designed to look and behave like a small internal platform — not a one-off script.

---

## What this is / is not

| This is | This is not |
|---------|-------------|
| A multi-source job **ingestion + intelligence** system | A mass spam auto-apply bot |
| An API-first backend with workers and storage | A LinkedIn scraper at scale |
| Explainable **RAG matching** for prioritization | A guarantee of interviews or offers |
| Optional personal tooling (apply agent is **disabled by default**) | Something to run against employers’ terms carelessly |

The optional Playwright apply agent (`run_apply.py`) is experimental and for personal use only. Respect each employer’s terms of service.

---

## Features

- **11 ATS / career sources** — Greenhouse, Ashby, Lever, Workday, Oracle, Amazon, SmartRecruiters, career portals, LinkedIn, Indeed, Glassdoor  
- **60+ companies** via YAML config and importable company packs  
- **NLP JD parsing** — skills ontology, seniority, years of experience, clearance, sponsorship flags  
- **RAG matching** — `sentence-transformers` embeddings, cosine similarity, optional OpenAI explanations (score, strengths, gaps)  
- **Background jobs** — Celery + Redis for hourly scan, embed, and alert schedules  
- **Company discovery** — detect ATS type from a careers URL and add it to config  
- **Multi-channel alerts** — email, Slack, Discord, Telegram with optional match scores  
- **API key auth** — optional multi-user mode with per-user preferences  
- **Web UI** — dashboard, jobs, matches, discover, settings  
- **Docker Compose** — API, worker, beat, Postgres, Redis in one command  

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  ATS APIs   │────▶│  FastAPI     │────▶│ PostgreSQL  │────▶│ RAG matcher  │
│  Scrapers   │     │  ingest/NLP  │     │ jobs/chunks │     │ + LLM score  │
└─────────────┘     └──────┬───────┘     └─────────────┘     └──────┬───────┘
                           │                                        │
                    ┌──────▼───────┐                         ┌──────▼───────┐
                    │ Celery/Redis │                         │ Email/Slack/ │
                    │ scan/embed/  │                         │ Discord/TG   │
                    │ alerts       │                         └──────────────┘
                    └──────────────┘
```

| Layer | Responsibility |
|-------|----------------|
| Scrapers | Rate-limited fetchers per ATS, plugin registry |
| API | REST endpoints for scan, jobs, profiles, matches, discovery |
| NLP | Structured fields from job descriptions |
| RAG | Chunk → embed → retrieve → score with evidence |
| Workers | Async pipeline on a schedule |
| Alerts | Multi-channel notifications with fit context |

---

## Tech stack

| Area | Tools |
|------|--------|
| Language | Python 3.9+ |
| API | FastAPI, Pydantic, Uvicorn |
| Data | PostgreSQL, SQLAlchemy, Alembic |
| Workers | Celery, Redis |
| ML / AI | sentence-transformers (`all-MiniLM-L6-v2`), OpenAI API (optional) |
| Automation | Playwright (optional apply agent) |
| Deploy | Docker, Docker Compose |
| UI | Jinja2 templates |

---

## Quick start

### CLI monitor (SQLite, email only)

```bash
git clone https://github.com/achyuthmanku-hub/job-opening-monitor.git
cd job-opening-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp companies.example.yaml companies.yaml
cp .env.example .env
# Edit .env with SMTP settings

python run.py --dry-run   # preview
python run.py --seed      # mark current jobs as seen
python run.py             # real run + email
```

### Full platform (Postgres + API + RAG)

```bash
# Postgres + Redis running locally, then:
createdb job_monitor   # or ./scripts/init_db.sh
alembic upgrade head

# In .env:
# DATABASE_URL=postgresql://localhost/job_monitor
# REDIS_URL=redis://localhost:6379/0
# OPENAI_API_KEY=...   # optional, improves match explanations

python run_api.py
```

Open:
- **Dashboard:** http://localhost:8000  
- **API docs:** http://localhost:8000/docs  
- **Matches UI:** http://localhost:8000/ui/matches  

### Docker (local)

```bash
docker compose up
```

Runs API, Celery worker, beat scheduler, Postgres, and Redis.

### Public URL for friends

See **[DEPLOY.md](DEPLOY.md)** — one-click Render/Railway deploy, then seed jobs from your laptop:

```bash
export DATABASE_URL='postgresql://...your-host...'
python scripts/seed_job_pool.py
# Friends: https://YOUR-APP.onrender.com/ui/upload
```

---

## Platform API

### Core workflow

```bash
# Scan jobs into Postgres
curl -X POST http://localhost:8000/jobs/scan

# View RAG matches
curl "http://localhost:8000/profiles/1/matches?min_score=70&refresh=true"

# Send smart alerts
curl -X POST http://localhost:8000/alerts/run
```

### Background workers (optional)

```bash
celery -A api.celery_app worker -l info
celery -A api.celery_app beat -l info
```

Beat schedule: scan hourly, embed, then alerts.

### Company discovery

```bash
curl -X POST http://localhost:8000/companies/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "https://jobs.ashbyhq.com/ramp", "company_name": "Ramp"}'

python scripts/import_company_pack.py us_tech.yaml
```

Or use the UI: http://localhost:8000/ui/discover

### Auth (optional)

```bash
python scripts/bootstrap_user.py --email you@example.com --name "Your Name"
# Set API_AUTH_ENABLED=true in .env
# Pass X-API-Key on write endpoints
```

---

## Smart alerts

In `config.yaml`:

```yaml
alerts:
  profile_id: 1
  min_match_score: 70
  include_match_scores: true
  channels:
    email: true
    slack: true
```

Webhooks in `.env`: `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

Example alert:

```
Stripe — Backend Engineer (91% fit)
Why: Java/Spring + payments experience aligns
Gap: Go preferred
https://...
```

---

## Configuration

Copy examples and customize (personal files are gitignored):

```bash
cp config.example.yaml config.yaml
cp companies.example.yaml companies.yaml
cp .env.example .env
```

### Supported company sources

| Type | Example |
|------|---------|
| `greenhouse` | `slug: stripe` |
| `ashby` | `slug: notion` |
| `lever` | `slug: plaid` |
| `workday` | `tenant`, `wd`, `site` |
| `oracle` | `host`, `site` |
| `amazon` | optional `query` |
| `career_portal` | full careers URL |

### Filters

```yaml
keywords:
  - "software engineer"

filters:
  us_only: true
  posted_min_hours: 1
  posted_max_hours: 25
  experience_max_years: 5
```

---

## Project layout

```
job-opening-monitor/
├── api/                    # FastAPI routes, services, Celery tasks, UI
├── src/
│   ├── scrapers/           # ATS fetchers + rate limiting
│   ├── nlp/                # JD parser
│   ├── rag/                # Embeddings + matching
│   ├── discovery/          # ATS auto-detection
│   └── notifier/           # Email + Slack/Discord/Telegram
├── data/company_packs/     # Importable company lists
├── alembic/                # Postgres migrations
├── run.py                  # CLI monitor
├── run_api.py              # API server
└── docker-compose.yml
```

---

## Limitations

- LinkedIn, Indeed, and Glassdoor may block automated requests — prefer ATS APIs.  
- First run emails all unseen jobs unless you seed the database.  
- RAG explanations use OpenAI when `OPENAI_API_KEY` is set; otherwise vector-only scoring.  
- Some career portals return 406/empty results; use Greenhouse/Ashby/Workday when possible.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Author

Built by [Achyuth Reddy Manku](https://github.com/achyuthmanku-hub) as a portfolio / personal productivity system demonstrating backend, data, and applied ML skills.

If this is useful, a ⭐ helps others find it.

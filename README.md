# Job Opening Monitor

A Python job intelligence platform that watches **50+ companies** across major ATS boards and career portals, filters for relevant US roles, emails you about **new** postings, and optionally runs an AI-assisted apply agent.

**Three modes:**

| Mode | Entry point | What it does |
|------|-------------|--------------|
| **Job monitor** | `run.py` | Hourly scrape → filter → email new jobs |
| **REST API** | `run_api.py` | FastAPI platform with DB storage + NLP parsing |
| **Apply agent** | `run_apply.py` | Optional auto-apply (separate from monitor) |

---

## Features

- **Multi-source scraping** — Greenhouse, Ashby, Lever, Workday, Oracle HCM, Amazon Jobs, career portals, LinkedIn
- **Smart filters** — US only, role keywords, posting time window (1–25h), experience years (0–5)
- **Email alerts** — Gmail SMTP; only notifies on jobs not seen before
- **FastAPI platform** — ingest jobs into Postgres/SQLite, search via REST, interactive docs at `/docs`
- **NLP parsing** — extracts skills, seniority, years required, clearance/sponsorship flags from job descriptions
- **Apply agent (optional)** — resume tailoring, match scoring, Playwright auto-submit for major ATS types

---

## Quick start

```bash
cd ~/job-opening-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp companies.example.yaml companies.yaml
cp application_profile.example.yaml application_profile.yaml
cp .env.example .env
# Edit companies.yaml, config.yaml, application_profile.yaml, and .env
```

### Job monitor (CLI)

```bash
# Preview matches — no email, nothing saved
python run.py --dry-run

# Mark current jobs as seen (recommended before first real run)
python run.py --seed

# Run once and email new jobs
python run.py
```

### Job intelligence API (Phase 1–2)

```bash
# Create database tables
./scripts/init_db.sh

# Start API server
python run_api.py
# Open http://localhost:8000/docs

# Scrape → store → enrich descriptions → NLP parse
curl -X POST http://localhost:8000/jobs/scan \
  -H "Content-Type: application/json" \
  -d '{"store_all": false, "enrich_descriptions": true, "parse_nlp": true}'

# Search parsed jobs
curl "http://localhost:8000/jobs?skill=java&seniority=mid&limit=10"

# Email new jobs (preview first)
curl -X POST "http://localhost:8000/alerts/run?dry_run=true"
curl -X POST http://localhost:8000/alerts/run
```

### Apply agent (optional, manual)

The apply agent is **disabled by default** in `config.yaml` (`apply_agent.enabled: false`) and is **not** run by the hourly monitor.

```bash
# Preview matches
python run_apply.py --force --dry-run

# Run apply agent
python run_apply.py --force

# View application history
python run_apply.py --list
```

---

## Schedule on macOS

```bash
chmod +x scripts/install_all_launchd.sh
./scripts/install_all_launchd.sh
```

| Scheduler | Schedule | Action |
|-----------|----------|--------|
| `com.jobopeningmonitor.agent` | Every hour | `run.py` — email new job postings |

Logs: `data/monitor.log`

Optional morning-only run (monitor only, no apply):

```bash
./scripts/install_morning_launchd.sh
```

---

## Configure companies

Edit `companies.yaml`. Each company can have multiple sources:

| Type | What to provide | Example |
|------|-----------------|---------|
| `greenhouse` | Board slug | `slug: stripe` |
| `lever` | Board slug | `slug: notion` |
| `ashby` | Board slug | `slug: linear` |
| `workday` | Tenant, data center, site | `tenant: ghr`, `wd: wd1`, `site: lateral-us` |
| `oracle` | Oracle host + site ID | `host: jpmc.fa.oraclecloud.com`, `site: CX_1001` |
| `amazon` | Optional search query | `query: ""` (all jobs) |
| `smartrecruiters` | Company slug | `slug: Visa` |
| `career_portal` | Full careers page URL | `url: https://www.notion.so/careers` |
| `linkedin` | Company jobs page URL | `url: https://www.linkedin.com/company/stripe/jobs` |
| `indeed` | Company jobs page URL | `url: https://www.indeed.com/cmp/Stripe/jobs` |
| `glassdoor` | Company jobs page URL | `url: https://www.glassdoor.com/Jobs/Stripe-Jobs-...` |

**Tip:** Structured APIs (Greenhouse, Workday, Oracle, Amazon) are the most reliable. Use career portals and LinkedIn as backups.

---

## Environment variables (`.env`)

```bash
# Email alerts (required for monitor)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFY_EMAIL=you@gmail.com

# API database (optional — defaults to SQLite)
# DATABASE_URL=postgresql://localhost/job_monitor

# Apply agent (optional)
OPENAI_API_KEY=sk-...
APPLY_EMAIL=you@gmail.com
APPLY_PASSWORD=your-portal-password
```

---

## Filters (`config.yaml`)

```yaml
keywords:
  - "software engineer"

filters:
  us_only: true
  posted_min_hours: 1
  posted_max_hours: 25
  allow_missing_posted_time: true
  experience_filter_enabled: true
  experience_min_years: 0
  experience_max_years: 5

apply_agent:
  enabled: false          # separate from hourly monitor
  min_match_score: 85
  max_applications_per_company: 1
  auto_submit: true
```

The hourly scheduler supports the 1–25 hour posting window reliably.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/jobs/scan` | Scrape, store, enrich, NLP parse |
| GET | `/jobs` | List jobs (`?company=&keyword=&skill=&seniority=`) |
| GET | `/jobs/new` | Jobs not yet emailed |
| GET | `/jobs/{id}/parsed` | NLP output for a job |
| POST | `/parse` | Run NLP on unparsed jobs |
| POST | `/alerts/run` | Send email for new jobs |
| GET | `/companies` | Companies in database |
| POST | `/profiles` | Save a resume profile |

Interactive docs: `http://localhost:8000/docs`

---

## How it works

### Job monitor (`run.py`)

1. Fetches jobs from all configured sources (~8,000 listings/run)
2. Filters by US, keywords, posting time, experience
3. Compares against `data/seen_jobs.db` (SQLite)
4. Emails new matches and marks them seen

### API platform (`run_api.py`)

1. Ingests filtered jobs into Postgres/SQLite (`data/job_platform.db` by default)
2. Fetches full job descriptions for NLP
3. Parses skills, seniority, years, clearance/sponsorship into `job_parsed`
4. Exposes search and alert endpoints via FastAPI

### Apply agent (`run_apply.py`)

1. Scores resume vs job description (OpenAI + keyword fallback)
2. Tailors resume in preserve mode (keeps your `.docx` layout)
3. Optionally auto-submits via Playwright (Greenhouse, Ashby, Workday, Oracle, Amazon, Lever)
4. Stores results in `data/applications.db`

---

## NLP skills ontology

Edit `data/skills_ontology.yaml` to add or map skills extracted from job descriptions.

Example parsed output:

```json
{
  "skills": ["java", "aws", "microservices"],
  "seniority": "mid",
  "min_years": 4,
  "requires_clearance": false,
  "sponsorship_mentioned": true
}
```

---

## Project layout

```
job-opening-monitor/
├── run.py                      # Job monitor CLI
├── run_api.py                  # FastAPI server
├── run_apply.py                # Apply agent CLI
├── companies.yaml              # Companies to watch
├── config.yaml                 # Filters and settings
├── application_profile.yaml    # Your profile (gitignored)
├── .env                        # Secrets (gitignored)
├── api/
│   ├── main.py                 # FastAPI app
│   ├── routes/                 # REST endpoints
│   ├── schemas/                # Pydantic models
│   └── services/               # Ingest, alerts, NLP pipeline
├── src/
│   ├── monitor.py              # Monitor orchestrator
│   ├── filters.py              # US / role / experience filters
│   ├── store.py                # SQLite dedup (monitor)
│   ├── notifier.py             # Email sender
│   ├── db/                     # SQLAlchemy models (API)
│   ├── nlp/                    # JD parser
│   ├── apply/                  # Apply agent + Playwright submitters
│   └── scrapers/               # Per-source fetchers
├── alembic/                    # Database migrations
├── data/
│   └── skills_ontology.yaml    # NLP skill mappings
└── scripts/
    ├── init_db.sh              # Run Alembic migrations
    ├── install_launchd.sh      # Hourly monitor scheduler
    └── install_all_launchd.sh  # One-command scheduler setup
```

---

## Limitations

- **LinkedIn, Indeed, and Glassdoor** may block automated requests — prefer ATS APIs
- **Career portals** use heuristic HTML parsing — some sites may fail (Meta 429, Uber 406)
- **Auto-apply** can be blocked by ATS anti-bot systems — use `max_applications_per_company: 1` and manual apply for sensitive companies
- **First monitor run** emails all current open jobs unless you run `--seed` first

---

## Roadmap

- [x] Phase 1 — FastAPI + database ingestion
- [x] Phase 2 — NLP skill/seniority extraction
- [ ] Phase 3 — RAG resume–job matching with explainable scores
- [ ] Phase 4 — Company auto-discovery + web dashboard

# Job Opening Monitor

A Python agent that watches company career portals, ATS boards (Greenhouse, Lever, Ashby), LinkedIn, Indeed, and Glassdoor — then emails you when new job postings appear.

## Quick start

```bash
cd ~/job-opening-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp companies.example.yaml companies.yaml
cp .env.example .env
# Edit companies.yaml with the companies you want to track
# Edit .env with your SMTP credentials
```

### Preview what would be detected (no email, nothing saved)

```bash
python run.py --dry-run
```

### Seed the database (recommended first step)

Marks all current jobs as "seen" so you only get emails for **new** postings going forward:

```bash
python run.py --seed
```

### Run for real

```bash
python run.py
```

### Schedule on macOS (twice daily at 9am and 5pm)

```bash
chmod +x scripts/install_launchd.sh
./scripts/install_launchd.sh
```

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

## Email setup (Gmail example)

1. Enable 2FA on your Google account
2. Create an [App Password](https://myaccount.google.com/apppasswords)
3. Set in `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
NOTIFY_EMAIL=you@gmail.com
```

## Filters (`config.yaml`)

```yaml
keywords:
  - "software engineer"   # title must contain this

filters:
  us_only: true          # United States only
  posted_min_hours: 1    # posted at least 1 hour ago
  posted_max_hours: 5    # posted at most 5 hours ago
```

The scheduler runs **every hour** so the 1–5 hour window is checked reliably.

Jobs without a precise posting timestamp (some career portals / LinkedIn) are skipped.

## How it works

1. Fetches jobs from all configured sources
2. Compares against a local SQLite database (`data/seen_jobs.db`)
3. Emails you about jobs it hasn't seen before
4. Records new jobs so you only get notified once

## Limitations

- **LinkedIn, Indeed, and Glassdoor** may block automated requests. Prefer ATS boards and direct career portals when possible.
- **Career portals** use heuristic HTML parsing — some sites may need custom selectors (open an issue or extend `career_portal.py`).
- First real run will email you about all currently open jobs (since none are in the database yet). Run `--dry-run` first to preview, or manually seed the database.

## Project layout

```
job-opening-monitor/
├── run.py                  # Entry point
├── companies.yaml          # Companies to watch (you create this)
├── config.yaml             # Settings (you create this)
├── .env                    # SMTP credentials (you create this)
├── src/
│   ├── monitor.py          # Main orchestrator
│   ├── store.py            # SQLite deduplication
│   ├── notifier.py         # Email sender
│   └── scrapers/           # Per-source fetchers
└── scripts/
    └── install_launchd.sh  # macOS scheduler
```

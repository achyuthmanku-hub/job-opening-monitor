# Deploy Job Intelligence (public URL for friends)

Friends open **`https://YOUR-APP.../ui/upload`**, upload a resume, and get matches.

You (operator) deploy once, then seed the shared job pool from your laptop.

---

## Recommended: Render (simple + public HTTPS)

### 1. Push code (already on `main`)

Repo: https://github.com/achyuthmanku-hub/job-opening-monitor

### 2. Create the service

1. Go to [https://render.com](https://render.com) → sign up with GitHub  
2. **New** → **Blueprint**  
3. Select `achyuthmanku-hub/job-opening-monitor`  
4. Apply `render.yaml` (creates **web service** + **Postgres**)  
5. Plan: use **Starter** for the web service if free tier runs out of memory (PyTorch/embeddings need ~1–2 GB RAM)

Or manually:

1. **New** → **PostgreSQL** (free) → copy **External Database URL**  
2. **New** → **Web Service** → this repo → **Docker**  
3. Environment:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Paste Postgres **Internal** URL (or External + `?sslmode=require`) |
| `IMPORT_FORTUNE500` | `true` |
| `API_AUTH_ENABLED` | `false` |
| `OPENAI_API_KEY` | optional |

4. Deploy. Public URL looks like:  
   `https://job-intelligence-api.onrender.com`

### 3. Seed jobs (from your Mac)

Scan is too long for an HTTP request on free hosts. Run it **locally against Render’s database**:

```bash
cd ~/job-opening-monitor
source .venv/bin/activate

# Use the External Database URL from Render (add ?sslmode=require if needed)
export DATABASE_URL='postgresql://USER:PASS@HOST/job_monitor?sslmode=require'

# companies.yaml must exist locally (Fortune 500 already imported on your machine)
python scripts/seed_job_pool.py
```

When it finishes, friends use:

```text
https://YOUR-SERVICE.onrender.com/ui/upload
```

### 4. Share the link

Send friends:

> Upload your resume here: https://YOUR-SERVICE.onrender.com/ui/upload

---

## Alternative: Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**  
2. Add **Postgres** plugin (sets `DATABASE_URL`)  
3. Variables: `IMPORT_FORTUNE500=true`  
4. Deploy uses `Dockerfile` + `railway.toml`  
5. **Settings → Networking → Generate domain**  
6. Seed the same way with Railway’s public `DATABASE_URL`:

```bash
export DATABASE_URL='postgresql://...'
python scripts/seed_job_pool.py
```

---

## Alternative: any VPS (DigitalOcean $4–6, Hetzner, etc.)

```bash
git clone https://github.com/achyuthmanku-hub/job-opening-monitor.git
cd job-opening-monitor
# set DATABASE_URL / secrets in .env
docker compose up -d postgres redis
docker compose up -d api
# seed
docker compose exec api python scripts/seed_job_pool.py
```

Point a domain + Caddy/Nginx for HTTPS.

---

## What friends see

| URL | Purpose |
|-----|---------|
| `/` | Landing page |
| `/ui/upload` | Upload resume → matches |
| `/ui/matches?profile_id=N` | Their results |
| `/docs` | API docs |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Deploy crashes / OOM | Upgrade to Starter (Render) or larger Railway instance |
| `/ui/upload` works but no matches | Run `scripts/seed_job_pool.py` against `DATABASE_URL` |
| `postgres://` errors | App normalizes to `postgresql://` automatically |
| Free Render sleeps | First request after idle can take 30–60s |
| Scan times out in browser | Always seed from your laptop, not `curl /jobs/scan` on free tier |

---

## Security notes (friends / public)

- Keep `API_AUTH_ENABLED=false` only for trusted friends on a private link.  
- For a wider audience, set `API_AUTH_ENABLED=true` and issue API keys.  
- Do not commit `.env` or real SMTP passwords.  
- Resume text is stored in Postgres — use a host you trust.

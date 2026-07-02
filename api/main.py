from fastapi import FastAPI

from api.routes import auth, companies, health, jobs, operations, profiles, tasks, ui

app = FastAPI(
    title="Job Intelligence Monitor",
    description="Phase 1–5 API: ingestion, NLP, RAG, discovery, workers, multi-user auth, and alerts.",
    version="0.5.0",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(operations.router)
app.include_router(profiles.router)
app.include_router(tasks.router)
app.include_router(ui.router)

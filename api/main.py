from fastapi import FastAPI

from api.routes import health, jobs, operations

app = FastAPI(
    title="Job Intelligence Monitor",
    description="Phase 1–2 API: ingestion, NLP parsing, and email alerts.",
    version="0.2.0",
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(operations.router)

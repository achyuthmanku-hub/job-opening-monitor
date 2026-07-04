from fastapi import FastAPI

from api.routes import auth, companies, health, jobs, operations, profiles, tasks, ui

app = FastAPI(
    title="Job Intelligence Monitor",
    description="Upload a resume, get personalized job matches from a shared ATS job pool.",
    version="0.6.0",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(operations.router)
app.include_router(profiles.router)
app.include_router(tasks.router)
app.include_router(ui.router)

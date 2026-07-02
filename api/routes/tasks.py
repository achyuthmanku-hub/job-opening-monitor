from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps.auth import require_user
from api.schemas.companies import TaskEnqueueResponse, TaskStatusResponse
from src.db.models import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/scan", response_model=TaskEnqueueResponse)
def enqueue_scan(
    store_all: bool = Query(default=False),
    enrich: bool = Query(default=True),
    parse: bool = Query(default=True),
    user: User = Depends(require_user),
) -> TaskEnqueueResponse:
    from api.tasks import scan_all_companies

    async_result = scan_all_companies.delay(store_all=store_all, enrich=enrich, parse_nlp=parse)
    return TaskEnqueueResponse(task_id=async_result.id, task_name="scan_all_companies")


@router.post("/alerts", response_model=TaskEnqueueResponse)
def enqueue_alerts(
    dry_run: bool = Query(default=False),
    user: User = Depends(require_user),
) -> TaskEnqueueResponse:
    from api.tasks import send_alerts_task

    async_result = send_alerts_task.delay(dry_run=dry_run)
    return TaskEnqueueResponse(task_id=async_result.id, task_name="send_alerts")


@router.post("/embed", response_model=TaskEnqueueResponse)
def enqueue_embed(
    profile_id: Optional[int] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_user),
) -> TaskEnqueueResponse:
    from api.tasks import embed_new_jobs_task

    async_result = embed_new_jobs_task.delay(profile_id=profile_id, limit=limit)
    return TaskEnqueueResponse(task_id=async_result.id, task_name="embed_new_jobs")


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str) -> TaskStatusResponse:
    from api.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    payload = None
    if result.ready() and result.successful():
        payload = result.result if isinstance(result.result, dict) else {"value": result.result}
    return TaskStatusResponse(
        task_id=task_id,
        state=result.state,
        ready=result.ready(),
        result=payload,
    )

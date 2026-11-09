"""Workflow execution logging: flows post their execution records here and
the backend writes them into the existing audit_events table (action
WORKFLOW_EXECUTION) — visible in the admin workflows monitor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..audit import log_event
from ..auth import AuthUser, get_current_user
from ..config import get_settings
from ..rate_limit import client_key, rate_limiter

router = APIRouter(prefix="/api/logs", tags=["workflow-logs"])


class ExecutionLogIn(BaseModel):
    flow: str = Field(min_length=1, max_length=120)
    status: str = Field(pattern="^(SUCCESS|ERROR|RUNNING)$")
    duration_ms: int = Field(ge=0, le=3_600_000)
    correlation_id: str = Field(default="", max_length=64)


@router.post("/execution")
def log_execution(
    payload: ExecutionLogIn,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    rate_limiter.check(
        f"logs:{client_key(request, user.id)}", settings.rate_limit_default_per_min
    )
    log_event(
        actor_id=user.id,
        actor_role=user.roles[0] if user.roles else None,
        action="WORKFLOW_EXECUTION",
        entity="workflows",
        entity_id=payload.flow,
        ip=request.client.host if request.client else None,
        metadata={
            "status": payload.status,
            "duration_ms": payload.duration_ms,
            "correlation_id": payload.correlation_id,
        },
    )
    return {"status": "logged"}

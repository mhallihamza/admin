"""Citizen process tracking (« Mes démarches »).

A citizen creates a process (e.g. a CNIE renewal follow-up), gets a
SUBMITTED timeline, and tracks every status change. Staff roles
(EMPLOYEE+) move the process forward. Every write is audited; ownership
is re-checked in the database on every read — the id alone proves
nothing."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .. import db
from ..audit import log_event
from ..auth import AuthUser, get_current_user, require_roles
from ..rate_limit import client_key, rate_limiter
from ..config import get_settings

router = APIRouter(prefix="/api/processes", tags=["processes"])

ALLOWED_TYPES = ("CNIE_RENEWAL", "PASSPORT", "BIRTH_ACT", "MARRIAGE", "DEATH_DECLARATION",
                 "COMPANY_REGISTRATION", "KAFALA", "CUSTOM")
ALLOWED_STATUSES = ("SUBMITTED", "IN_REVIEW", "ACTION_REQUIRED", "COMPLETED", "REJECTED")
STAFF_ROLES = ("EMPLOYEE", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN")


class ProcessIn(BaseModel):
    process_type: str = Field(default="CUSTOM", max_length=40)
    title: str = Field(min_length=3, max_length=120)


class StatusIn(BaseModel):
    status: str = Field(min_length=3, max_length=30)
    note: str = Field(default="", max_length=500)


def _validate_choice(value: str, allowed: tuple[str, ...], label: str) -> str:
    if value not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{label} invalide : {value}")
    return value


@router.post("", status_code=status.HTTP_201_CREATED)
def create_process(
    payload: ProcessIn,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    rate_limiter.check(
        f"processes:{client_key(request, user.id)}", settings.rate_limit_default_per_min
    )
    process_type = _validate_choice(payload.process_type.upper(), ALLOWED_TYPES, "type")
    row = db.fetch_one(
        "insert into citizen_processes (user_id, process_type, title, status)"
        " values (%s, %s, %s, 'SUBMITTED')"
        " returning id, process_type, title, status, created_at",
        (user.id, process_type, payload.title.strip()),
    )
    if not row:
        raise HTTPException(status_code=503, detail="Store unreachable")
    db.execute(
        "insert into citizen_process_events (process_id, status, note, created_by)"
        " values (%s, 'SUBMITTED', 'Création de la démarche', %s)",
        (row["id"], user.id),
    )
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="PROCESS_CREATED", entity="citizen_processes",
              entity_id=str(row["id"]), metadata={"type": process_type})
    return {"process": {k: str(v) for k, v in row.items()}}


@router.get("")
def list_processes(user: AuthUser = Depends(get_current_user)) -> dict:
    rows = db.fetch_all(
        "select p.id, p.process_type, p.title, p.status, p.created_at, p.updated_at,"
        " (select count(*) from citizen_process_events e where e.process_id = p.id) as events"
        " from citizen_processes p where p.user_id = %s order by p.created_at desc limit 100",
        (user.id,),
    )
    return {"processes": [{**r, "id": str(r["id"])} for r in rows]}


@router.get("/{process_id}")
def process_detail(process_id: str, user: AuthUser = Depends(get_current_user)) -> dict:
    try:
        pid = str(uuid_mod.UUID(process_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="id invalide")
    row = db.fetch_one(
        "select id, user_id, process_type, title, status, created_at, updated_at"
        " from citizen_processes where id = %s",
        (pid,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Démarche introuvable")
    is_owner = str(row["user_id"]) == user.id
    is_staff = user.has_any_role(*STAFF_ROLES)
    if not (is_owner or is_staff):
        # accès aux données d'un autre citoyen : refus net
        raise HTTPException(status_code=403, detail="Accès refusé")
    events = db.fetch_all(
        "select status, note, created_at from citizen_process_events"
        " where process_id = %s order by created_at asc",
        (pid,),
    )
    return {"process": {k: str(v) for k, v in row.items()},
            "events": [{k: str(v) for k, v in e.items()} for e in events]}


@router.patch("/{process_id}/status")
def update_status(
    process_id: str,
    payload: StatusIn,
    user: AuthUser = Depends(require_roles(*STAFF_ROLES)),
) -> dict:
    new_status = _validate_choice(payload.status.upper(), ALLOWED_STATUSES, "statut")
    try:
        pid = str(uuid_mod.UUID(process_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="id invalide")
    row = db.fetch_one("select id, user_id from citizen_processes where id = %s", (pid,))
    if not row:
        raise HTTPException(status_code=404, detail="Démarche introuvable")
    db.execute(
        "update citizen_processes set status = %s, updated_at = now() where id = %s",
        (new_status, pid),
    )
    db.execute(
        "insert into citizen_process_events (process_id, status, note, created_by)"
        " values (%s, %s, %s, %s)",
        (pid, new_status, payload.note, user.id),
    )
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="PROCESS_STATUS_CHANGED", entity="citizen_processes",
              entity_id=pid, metadata={"status": new_status})
    return {"id": pid, "status": new_status}

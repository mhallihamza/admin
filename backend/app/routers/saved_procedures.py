"""Saved procedures (« Procédures enregistrées ») — real per-user
persistence replacing the Phase-3 sample store. Ownership re-checked in
the database on every read; every write audited."""

from __future__ import annotations

import json
import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import db
from ..audit import log_event
from ..auth import AuthUser, get_current_user
from ..routers.chat import _clean_agent_markers

router = APIRouter(prefix="/api/procedures", tags=["saved-procedures"])


class SaveIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    snapshot: dict = Field(default_factory=dict)


@router.get("/saved/{procedure_id}")
def get_saved(procedure_id: str, user: AuthUser = Depends(get_current_user)) -> dict:
    try:
        candidate = str(uuid_mod.UUID(procedure_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="id invalide") from exc

    row = db.fetch_one(
        "select id, title, procedure_snapshot, created_at from saved_procedures where id = %s and user_id = %s",
        (candidate, user.id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Procédure introuvable")
    title = _clean_agent_markers(str(row.get("title") or "")).strip() or "Procédure enregistrée"
    snapshot = row.get("procedure_snapshot") or {}
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except (ValueError, TypeError):
            snapshot = {"answer": snapshot}
    if not isinstance(snapshot, dict):
        snapshot = {"answer": str(snapshot)}
    return {
        "saved": {
            "id": str(row["id"]),
            "title": title,
            "snapshot": snapshot,
            "created_at": row["created_at"].isoformat().replace("+00:00", "") if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        }
    }


@router.get("/saved")
def list_saved(user: AuthUser = Depends(get_current_user)) -> dict:
    rows = db.fetch_all(
        "select id, title, created_at from saved_procedures"
        " where user_id = %s order by created_at desc limit 100",
        (user.id,),
    )

    def clean_title(raw: str) -> str:
        title = _clean_agent_markers(raw).strip()
        if not title:
            return "Procédure enregistrée"
        return title

    return {"saved": [{**{k: str(v) for k, v in r.items() if k != "title"},
                        "title": clean_title(str(r.get("title") or ""))} for r in rows]}


def _safe_title(payload_title: str, snapshot: dict) -> str:
    title = _clean_agent_markers(payload_title).strip()
    if title:
        return title[:160]
    answer = str((snapshot or {}).get("answer") or "")
    for line in answer.splitlines():
        candidate = _clean_agent_markers(line).strip()
        if len(candidate) >= 3:
            return candidate[:160]
    return "Procédure enregistrée"


@router.post("/saved", status_code=201)
def save_procedure(payload: SaveIn, user: AuthUser = Depends(get_current_user)) -> dict:
    title = _safe_title(payload.title, payload.snapshot)
    row = db.fetch_one(
        "insert into saved_procedures (user_id, title, procedure_snapshot)"
        " values (%s, %s, %s)"
        " on conflict (user_id, title) do update set created_at = now()"
        " returning id, title, created_at",
        (user.id, title, json.dumps(payload.snapshot, ensure_ascii=False)[:4000]),
    )
    if not row:
        raise HTTPException(status_code=503, detail="Store unreachable")
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="PROCEDURE_SAVED", entity="saved_procedures",
              entity_id=str(row["id"]))
    return {"saved": {k: str(v) for k, v in row.items()}}


@router.delete("/saved/{procedure_id}", status_code=204)
def delete_saved(procedure_id: str, user: AuthUser = Depends(get_current_user)) -> None:
    try:
        pid = str(uuid_mod.UUID(procedure_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="id invalide")
    db.execute(
        "delete from saved_procedures where id = %s and user_id = %s",
        (pid, user.id),
    )
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="PROCEDURE_DELETED", entity="saved_procedures", entity_id=pid)
    return None

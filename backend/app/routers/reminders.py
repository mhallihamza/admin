"""Private citizen "Mes démarches" notebook.

Personal reminders/notes only — the platform does not process official
applications such as CNIE or passports here. Every row is private and
scoped to the verified user; nothing is routed to an administration.
"""

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .. import db
from ..audit import log_event
from ..auth import AuthUser, require_roles

router = APIRouter(prefix="/api/reminders", tags=["citizen-reminders"])

_CITIZEN = ("CITIZEN", "EMPLOYEE", "CONTENT_APPROVER", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN")


class ReminderIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=2000)


class ReminderPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)
    status: str | None = None


def _row(row: dict[str, Any]) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "notes": row.get("notes") or "",
        "status": row.get("status") or "OPEN",
        "createdAt": _iso(row.get("created_at")),
        "updatedAt": _iso(row.get("updated_at")),
    }


def _iso(value: Any) -> str:
    try:
        return value.isoformat().replace("+00:00", "")
    except Exception:
        return str(value or "")


@router.get("")
def list_reminders(user: AuthUser = Depends(require_roles(*_CITIZEN))) -> dict:
    rows = db.fetch_all(
        """
        select id, title, notes, status, created_at, updated_at
        from citizen_reminders
        where user_id = %s
        order by status asc, updated_at desc
        limit 200
        """,
        (user.id,),
    )
    return {"reminders": [_row(row) for row in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderIn, user: AuthUser = Depends(require_roles(*_CITIZEN))) -> dict:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Titre requis")
    notes = payload.notes.strip()
    row = db.fetch_one(
        """
        insert into citizen_reminders (user_id, title, notes)
        values (%s, %s, %s)
        returning id, title, notes, status, created_at, updated_at
        """,
        (user.id, title, notes),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rappel non créé")
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="CITIZEN_REMINDER_SAVED", entity="citizen_reminders", entity_id=str(row["id"]))
    return _row(row)


@router.patch("/{reminder_id}")
def update_reminder(reminder_id: str, payload: ReminderPatchIn,
                    user: AuthUser = Depends(require_roles(*_CITIZEN))) -> dict:
    try:
        candidate = str(uuid_mod.UUID(reminder_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reminder id invalide") from exc

    status_value = (payload.status or "").upper() or None
    if status_value and status_value not in ("OPEN", "DONE"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Statut invalide")

    title = payload.title.strip() if payload.title is not None else None
    notes = payload.notes.strip() if payload.notes is not None else None
    row = db.fetch_one(
        """
        update citizen_reminders
        set title = coalesce(%s, title),
            notes = coalesce(%s, notes),
            status = coalesce(%s, status),
            updated_at = now()
        where id = %s and user_id = %s
        returning id, title, notes, status, created_at, updated_at
        """,
        (title, notes, status_value, candidate, user.id),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rappel introuvable")
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="CITIZEN_REMINDER_UPDATED", entity="citizen_reminders", entity_id=candidate,
              metadata={"status": status_value})
    return _row(row)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: str, user: AuthUser = Depends(require_roles(*_CITIZEN))) -> None:
    try:
        candidate = str(uuid_mod.UUID(reminder_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reminder id invalide") from exc
    db.execute(
        "delete from citizen_reminders where id = %s and user_id = %s",
        (candidate, user.id),
    )
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action="CITIZEN_REMINDER_DELETED", entity="citizen_reminders", entity_id=candidate)

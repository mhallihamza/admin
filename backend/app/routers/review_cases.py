"""Human review queue — real rows in `review_cases`, with audited decisions.

Staff read/write; citizen can create a visible `/api/review-cases/request`
case instead of a local UI toggle.
"""

from __future__ import annotations

import json
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .. import db
from ..audit import log_event
from ..auth import AuthUser, get_current_user, require_roles

router = APIRouter(prefix="/api/review-cases", tags=["review-cases"])

_STAFF = ("EMPLOYEE", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN")


class ReviewRequestIn(BaseModel):
    question_summary: str = Field(min_length=3, max_length=500)
    proposed_answer: str | None = ""
    conversation_id: str | None = None


class ReviewPatchIn(BaseModel):
    status: str
    note: str | None = ""
    service_name: str | None = ""


_VALID_STATUS = {"OPEN", "IN_REVIEW", "APPROVED", "CORRECTED", "REJECTED", "TRANSFERRED"}
_NOTE_REQUIRED = {"CORRECTED", "REJECTED"}


def _iso(value: Any) -> str:
    try:
        iso = value.isoformat()
    except Exception:
        return str(value)
    return iso.replace("+00:00", "")


def _row(row: dict[str, Any]) -> dict:
    evidence = row.get("legal_evidence") or []
    if isinstance(evidence, str):
        try:
            evidence = json.loads(evidence)
        except (ValueError, TypeError):
            evidence = [evidence]
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    return {
        "id": str(row["id"]),
        "question_summary": row["question_summary"],
        "question": row.get("question") or row["question_summary"],
        "proposed_answer": row.get("proposed_answer") or "",
        "legal_evidence": [str(item) for item in evidence],
        "risk": row["risk_level"],
        "status": row["status"],
        "service_name": row.get("service_name") or "",
        "requested_by": row.get("requested_by_email") or "",
        "created_at": _iso(row["created_at"]),
    }


_SELECT = """
    select rc.id, rc.question_summary, rc.proposed_answer, rc.legal_evidence,
           rc.risk_level, rc.status, rc.service_name, rc.created_at,
           m.content as question,
           p.email as requested_by_email
    from review_cases rc
    left join messages m on m.id = rc.message_id
    left join profiles p on p.id = rc.requested_by
"""


def create_review_case(user_id: str | None, question: str, *,
                       conversation_id: str | None = None,
                       proposed_answer: str = "",
                       risk_level: str = "MEDIUM",
                       actor_role: str | None = None,
                       action: str = "REVIEW_REQUESTED") -> str | None:
    """Crée un dossier de revue réel. Utilisé pour la revue manuelle et
    pour les cas automatiques (réponse retenue / indisponible)."""
    risk = risk_level.upper() if risk_level else "MEDIUM"
    if risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        risk = "MEDIUM"
    question = str(question or "").strip()[:500]
    proposed = str(proposed_answer or "").strip()[:4000]
    if len(question) < 3:
        question = proposed[:500]
    if len(question) < 3:
        question = "Question insuffisamment précise — revue humaine requise."
    candidate = None
    if conversation_id:
        try:
            candidate = str(uuid_mod.UUID(str(conversation_id)))
        except ValueError:
            candidate = None
    row = db.fetch_one(
        """
        insert into review_cases
            (conversation_id, requested_by, question_summary, proposed_answer, risk_level)
        values (%s, %s, %s, %s, %s::risk_level)
        returning id
        """,
        (candidate, user_id, question, proposed, risk),
    )
    case_id = str(row["id"]) if row else None
    if case_id:
        log_event(actor_id=user_id, actor_role=actor_role,
                  action=action, entity="review_cases", entity_id=case_id)
    return case_id


@router.get("")
def list_review_cases(user: AuthUser = Depends(require_roles(*_STAFF))) -> dict:
    rows = db.fetch_all(
        _SELECT + " order by rc.created_at desc limit 200"
    )
    return {"review_cases": [_row(row) for row in rows]}


@router.get("/{case_id}")
def get_review_case(case_id: str, user: AuthUser = Depends(require_roles(*_STAFF))) -> dict:
    try:
        candidate = str(uuid_mod.UUID(case_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="case id invalide") from exc
    row = db.fetch_one(_SELECT + " where rc.id = %s", (candidate,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    return _row(row)


@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_review(payload: ReviewRequestIn, user: AuthUser = Depends(get_current_user)) -> dict:
    candidate = None
    if payload.conversation_id:
        try:
            candidate = str(uuid_mod.UUID(payload.conversation_id))
        except ValueError:
            candidate = None
        if candidate:
            owned = db.fetch_one(
                "select id from conversations where id = %s and user_id = %s",
                (candidate, user.id),
            )
            if not owned:
                candidate = None
    case_id = create_review_case(
        user.id, payload.question_summary.strip(),
        conversation_id=candidate,
        proposed_answer=(payload.proposed_answer or "").strip(),
        risk_level="MEDIUM",
        actor_role=user.roles[0] if user.roles else None,
        action="REVIEW_REQUESTED",
    )
    if not case_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dossier non créé")
    row = db.fetch_one(_SELECT + " where rc.id = %s", (case_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dossier créé, mais lecture impossible")
    return _row(row)


@router.patch("/{case_id}")
def update_review_case(case_id: str, payload: ReviewPatchIn,
                       user: AuthUser = Depends(require_roles(*_STAFF))) -> dict:
    status_value = payload.status.upper()
    note = (payload.note or "").strip()
    service_name = (payload.service_name or "").strip()
    if status_value not in _VALID_STATUS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Statut invalide")
    if status_value in _NOTE_REQUIRED and not note:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Une note est requise pour corriger ou refuser le dossier.")
    if status_value == "TRANSFERRED" and not service_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Un service destinataire est requis.")

    try:
        candidate = str(uuid_mod.UUID(case_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="case id invalide") from exc

    row = db.fetch_one(
        """
        update review_cases
        set status = %s::review_case_status,
            service_name = coalesce(%s, service_name),
            resolution_note = %s,
            updated_at = now()
        where id = %s
        returning id, question_summary, proposed_answer, legal_evidence,
                  risk_level, status, service_name, created_at
        """,
        (status_value, service_name or None, note or None, candidate),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    log_event(
        actor_id=user.id,
        actor_role=user.roles[0] if user.roles else None,
        action=f"REVIEW_CASE_{status_value}",
        entity="review_cases",
        entity_id=candidate,
        metadata={"note": note, "service_name": service_name},
    )
    return _row(row | {"question": row["question_summary"]})

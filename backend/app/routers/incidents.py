"""Security incident reads / reveal for auditors and admins.
Blocked user text is never returned without a reason and is audited every
time an authorized reviewer reveals it."""

from __future__ import annotations

import json
import ipaddress
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import db
from ..audit import log_event
from ..auth import AuthUser, require_roles

router = APIRouter(prefix="/api/security", tags=["security-incidents"])

_ROLES = ("SECURITY_AUDITOR", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN")


class RevealIn(BaseModel):
    reason: str


def _iso(value: Any) -> str:
    try:
        return value.isoformat().replace("+00:00", "")
    except Exception:
        return str(value)


def _mask_ip(value: Any) -> str:
    if value is None:
        return ""
    try:
        ip = ipaddress.ip_address(str(value))
    except ValueError:
        return str(value)
    if ip.version == 4:
        parts = str(ip).split(".")
        return ".".join(parts[:2] + ["x", "x"])
    return ":".join(str(ip).split(":")[:2] + ["x", "x"])


def _incident_row(row: dict[str, Any], include_metadata: bool = False) -> dict:
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (ValueError, TypeError):
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    flagged = metadata.get("flagged_text")
    return {
        "id": str(row["id"]),
        "attackType": row.get("attack_type") or "GATE_LAYER1",
        "risk": row.get("risk_level") or "LOW",
        "decision": row.get("decision") or "BLOCK",
        "sourceIp": _mask_ip(row.get("source_ip")),
        "reason": row.get("reason") or "",
        "createdAt": _iso(row["created_at"]),
        "hasConversationContent": bool(flagged),
        "conversationId": str(metadata.get("conversation_id") or ""),
        "route": str(metadata.get("route") or ""),
        **({"conversationContent": str(flagged)} if include_metadata and flagged else {}),
    }


@router.get("/incidents")
def list_incidents(limit: int = Query(50, ge=1, le=100),
                   user: AuthUser = Depends(require_roles(*_ROLES))) -> dict:
    rows = db.fetch_all(
        """
        select id, source_ip, attack_type, risk_level, decision, reason, metadata, created_at
        from security_incidents
        order by created_at desc
        limit %s
        """,
        (limit,),
    )
    return {"incidents": [_incident_row(row) for row in rows]}


@router.get("/blocked-requests")
def list_blocked_requests(limit: int = Query(50, ge=1, le=100),
                          user: AuthUser = Depends(require_roles(*_ROLES))) -> dict:
    rows = db.fetch_all(
        """
        select id, source_ip, attack_type, risk_level, decision, reason, metadata, created_at
        from security_incidents
        where decision in ('BLOCK', 'REVIEW', 'RESTRICT')
        order by created_at desc
        limit %s
        """,
        (limit,),
    )
    return {"blockedRequests": [{
        "id": item["id"], "attackType": item["attackType"],
        "risk": item["risk"], "decision": item["decision"],
        "route": item["route"] or "/api/chat/message",
        "createdAt": item["createdAt"],
    } for item in (_incident_row(row) for row in rows)]}


@router.post("/incidents/{incident_id}/reveal")
def reveal_incident(incident_id: str, payload: RevealIn,
                    user: AuthUser = Depends(require_roles(*_ROLES))) -> dict:
    reason = payload.reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Une raison d'au moins 3 caractères est requise.")
    try:
        candidate = str(uuid_mod.UUID(incident_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="incident id invalide") from exc

    row = db.fetch_one(
        "select id, metadata from security_incidents where id = %s",
        (candidate,),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident introuvable")
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (ValueError, TypeError):
            metadata = {}
    flagged = metadata.get("flagged_text") if isinstance(metadata, dict) else None
    if not flagged:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Aucun contenu de conversation n'a été capturé pour cet incident.")

    # Audit obligatoire avant divulgation : le motif et l'identité du demandeur.
    log_event(
        actor_id=user.id,
        actor_role=user.roles[0] if user.roles else None,
        action="CONVERSATION_CONTENT_REVEALED",
        entity="security_incidents",
        entity_id=candidate,
        metadata={"motif": reason},
    )
    return {"conversationContent": str(flagged), "conversationId": str(metadata.get("conversation_id") or "")}


"""Citizen chat entry point. Every message passes the security gate
(Layer 1 fixed rules; Layer 2 standalone LangGraph workflow service) before
anything else. On ALLOW, the message is forwarded to the same service's
/run/pipeline (LangGraph flows 06+07+09), mirroring how Langflow was
chained to ALLOW before.

Conversation memory (2026-11): messages are persisted in the existing
conversations/messages tables; the last exchanges are passed to the
workflow so follow-up questions keep their context."""

from __future__ import annotations

import os
import uuid as uuid_mod
from types import SimpleNamespace

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import db
from ..audit import log_event, log_incident
from ..auth import AuthUser, get_current_user
from .review_cases import create_review_case
from ..rate_limit import client_key, rate_limiter
from ..security_gate import BLOCK, REVIEW, run_security_gate
from ..validation import ChatMessageIn
from ..config import get_settings

router = APIRouter(prefix="/api/chat", tags=["chat"])

HISTORY_TURNS = 6  # messages (user+assistant) envoyés au pipeline


import re


def _clean_agent_markers(text: str) -> str:
    """Marqueurs d'agent internes — jamais montrés côté citoyen."""
    value = str(text or "")
    value = re.sub(r"(?im)^\s*\[(?:PROCEDURE|LEGAL_RESEARCH|DOCUMENT_ADMIN|SUPERVISOR|DETECTION)_AGENT\]\s*\n?", "", value)
    return value.strip()


def _owned_conversation(user: AuthUser, conversation_id: str | None,
                        first_text: str, locale: str) -> str:
    """Retourne l'id d'une conversation appartenant à l'utilisateur, ou en
    crée une. L'appartenance est revérifiée en base — jamais l'entrée
    utilisateur seule."""
    if conversation_id:
        try:
            candidate = str(uuid_mod.UUID(conversation_id))
        except ValueError:
            candidate = ""
        if candidate:
            row = db.fetch_one(
                "select id from conversations where id = %s and user_id = %s",
                (candidate, user.id),
            )
            if row:
                return candidate
    row = db.fetch_one(
        "insert into conversations (user_id, title, locale)"
        " values (%s, %s, %s) returning id",
        (user.id, first_text[:60], locale),
    )
    return row["id"] if row else ""


def _save_message(conversation_id: str, role: str, content: str) -> None:
    db.execute(
        "insert into messages (conversation_id, role, content) values (%s, %s, %s)",
        (conversation_id, role, content[:2000]),
    )


def _history(conversation_id: str) -> list[dict[str, str]]:
    rows = db.fetch_all(
        "select role, content from messages where conversation_id = %s"
        " order by created_at desc limit %s",
        (conversation_id, HISTORY_TURNS),
    )
    return [{"role": r["role"].lower(), "text": r["content"]}
            for r in reversed(rows)]


@router.get("/messages")
def conversation_messages(
    conversation_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    """Historique d'une conversation — propriété vérifiée en base."""
    try:
        candidate = str(uuid_mod.UUID(conversation_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="conversation_id invalide")
    owned = db.fetch_one(
        "select id from conversations where id = %s and user_id = %s",
        (candidate, user.id),
    )
    if not owned:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conversation introuvable")
    rows = db.fetch_all(
        "select id, role, content, created_at from messages"
        " where conversation_id = %s order by created_at asc limit 200",
        (candidate,),
    )
    return {"conversation_id": candidate,
            "messages": [{"id": str(r["id"]), "role": r["role"].lower(),
                          "text": _clean_agent_markers(r["content"])} for r in rows]}


@router.post("/message")
def send_message(
    payload: ChatMessageIn,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    # Rate limit before any processing.
    rate_limiter.check(
        f"chat:{client_key(request, user.id)}", settings.rate_limit_chat_per_min
    )

    verdict = run_security_gate(
        SimpleNamespace(request_type="chat", text=payload.text, filename=None, source_user_id=None, agent=None, tool=None),
        user,
    )

    if verdict.decision in (BLOCK, REVIEW):
        detail = (
            "Request blocked by the security gate."
            if verdict.decision == BLOCK
            else "Message flagged for human review."
        )
        review_case_id = create_review_case(
            user.id, payload.text,
            proposed_answer=verdict.reason or "",
            risk_level="HIGH",
            actor_role=user.roles[0] if user.roles else None,
            action=f"AUTO_REVIEW_{verdict.decision}",
        )
        log_incident(
            user_id=user.id,
            source_ip=request.client.host if request.client else None,
            attack_type={
                BLOCK: "PROMPT_INJECTION",
                REVIEW: None,
            }.get(verdict.decision),
            risk_level="HIGH",
            decision=verdict.decision,
            reason=verdict.reason or detail,
            metadata={
                "route": str(request.url.path),
                "flagged_text": payload.text,
                "conversation_id": payload.conversation_id or "",
                "review_case_id": review_case_id or "",
            },
        )
        if verdict.decision == BLOCK:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
                headers={"X-Review-Case-ID": review_case_id or ""},
            )
        return {"decision": "review", "detail": detail, "review_case_id": review_case_id}

    # Mémoire de conversation : conversation possédée ou créée, message
    # utilisateur persisté avant le pipeline, réponse persistée après.
    conversation_id = ""
    history: list[dict[str, str]] = []
    persistence_error: str | None = None
    try:
        conversation_id = _owned_conversation(user, payload.conversation_id,
                                              payload.text, payload.locale)
        if conversation_id:
            history = _history(conversation_id)
            _save_message(conversation_id, "USER", payload.text)
    except Exception as exc:  # noqa: BLE001 — la réponse ne dépend pas de la persistance
        persistence_error = str(exc)[:120]

    log_event(
        actor_id=user.id,
        actor_role=user.roles[0] if user.roles else None,
        action="CHAT_MESSAGE_ACCEPTED",
        entity="conversations",
        entity_id=conversation_id or payload.conversation_id,
        ip=request.client.host if request.client else None,
    )

    # Phase 5: ALLOW → the LangGraph workflow service answers the question
    # (flows 06 → 07 → 09 over HTTP, replacing the Langflow chaining).
    # Without LANGGRAPH_BASE_URL (offline/dev) the legacy placeholder reply
    # is kept so the existing tests stay meaningful.
    base_url = settings.langgraph_base_url.rstrip("/")
    if not base_url:
        return {
            "decision": "allow",
            "detail": "Accepted by the security gate. Answer pipeline connects in Phase 5.",
            "conversation_id": conversation_id,
        }

    workflow_result = _run_langgraph_pipeline(base_url, settings, request, user,
                                              payload, history)
    if workflow_result is None:
        # Fail-closed on transport errors: never answer from nothing.
        review_case_id = create_review_case(
            user.id, payload.text,
            conversation_id=conversation_id or None,
            proposed_answer="",
            risk_level="HIGH",
            actor_role=user.roles[0] if user.roles else None,
            action="AUTO_REVIEW_OUTAGE",
        )
        return {
            "decision": "review",
            "detail": "Workflow service unreachable — answer withheld for review.",
            "conversation_id": conversation_id,
            "review_case_id": review_case_id,
        }

    decision = workflow_result.get("gate_decision") or "ALLOW"
    if decision != "ALLOW":
        reason = workflow_result.get("gate_reason") or "Answer validation failed."
        review_case_id = create_review_case(
            user.id, payload.text,
            conversation_id=conversation_id or None,
            proposed_answer=reason,
            risk_level="HIGH" if decision in ("REVIEW", "BLOCK", "RESTRICT") else "MEDIUM",
            actor_role=user.roles[0] if user.roles else None,
            action=f"AUTO_REVIEW_{decision.upper()}",
        )
        log_incident(
            user_id=user.id,
            source_ip=request.client.host if request.client else None,
            attack_type=(workflow_result.get("layer2") or {}).get("attack_type"),
            risk_level="HIGH",
            decision=decision,
            reason=workflow_result.get("gate_reason") or "Answer validation failed.",
            metadata={
                "route": str(request.url.path),
                "flagged_text": payload.text,
                "conversation_id": conversation_id or (payload.conversation_id or ""),
                "review_case_id": review_case_id or "",
            },
        )
        return {
            "decision": decision.lower(),
            "detail": "Response withheld by the answer validation gate.",
            "conversation_id": conversation_id,
            "review_case_id": review_case_id,
        }

    answer_text = _clean_agent_markers(workflow_result.get("answer") or "")
    if conversation_id and answer_text:
        try:
            _save_message(conversation_id, "ASSISTANT", answer_text)
        except Exception:  # noqa: BLE001 — persistance best-effort
            pass

    return {
        "decision": "allow",
        "answer": workflow_result.get("answer") and answer_text or None,
        "specialist": workflow_result.get("specialist"),
        "citations": workflow_result.get("citations", []),
        "conversation_id": conversation_id,
        "persistence_error": persistence_error,
    }


def _run_langgraph_pipeline(base_url, settings, request: Request, user: AuthUser,
                            payload, history: list[dict[str, str]]) -> dict | None:
    """POST the allowed question to the workflow service /run/pipeline."""
    headers = {}
    if settings.langgraph_flow_token:
        headers["X-Flow-Token"] = settings.langgraph_flow_token
    try:
        response = httpx.post(
            f"{base_url}/run/pipeline",
            json={
                "question": payload.text,
                "language": payload.locale,
                "conversation_id": payload.conversation_id or "",
                "user_id": user.id,
                "roles": user.roles,
                "user_token": request.headers.get("authorization", "").removeprefix("Bearer "),
                "gateway_base_url": settings.backend_public_url,
                "history": history,
            },
            headers=headers,
            timeout=300.0,
        )
        if response.status_code == 200:
            return response.json()
    except (httpx.HTTPError, ValueError):
        return None
    return None

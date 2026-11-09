"""Tool gateway endpoints — one endpoint per tool. Every call requires:
- a verified user session token, and
- a short-lived agent token (X-Agent-Token) issued per request by
  POST /api/gateway/token after permission checks.

The endpoint re-validates user + role + agent + tool + operation + data
scope against the permission tables and audits every denial. After the
checks, the tool executes against the Phase 5 LangGraph workflow service
(retrievals are proxied through it; document-index reads this backend's
own documents table; human-handoff writes a review_cases row). When
LANGGRAPH_BASE_URL is unset the retrievals keep the offline Phase-4
acknowledgement behaviour."""

from __future__ import annotations

import uuid as uuid_mod

import httpx
from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..audit import log_event
from ..auth import AuthUser, get_current_user
from ..config import get_settings
from ..gateway import AgentTokenPayload, require_agent_token
from ..validation import (
    DocumentIndexIn,
    GraphRetrievalIn,
    HumanHandoffIn,
    VectorRetrievalIn,
)

router = APIRouter(prefix="/api", tags=["tool-gateway"])


def _accepted(tool: str, payload: AgentTokenPayload) -> dict:
    return {
        "status": "accepted",
        "tool": tool,
        "agent": payload.agent,
        "data_scope": payload.data_scope,
        "note": "Permission checks passed. Workflow execution connects in Phase 5.",
    }


def _langgraph(path: str, payload: dict) -> dict | None:
    """Proxy the checked tool call to the LangGraph service. Returns None
    when the service is not configured (callers keep the Phase-4 ack)."""
    settings = get_settings()
    if not settings.langgraph_base_url:
        return None
    headers = {"Content-Type": "application/json"}
    if settings.langgraph_flow_token:
        headers["X-Flow-Token"] = settings.langgraph_flow_token
    try:
        response = httpx.post(
            f"{settings.langgraph_base_url.rstrip('/')}{path}",
            json=payload,
            headers=headers,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        return {"status": "error", "error": f"LangGraph service unreachable: {exc}"[:200]}
    if response.status_code != 200:
        return {"status": "error",
                "error": f"LangGraph service returned {response.status_code}",
                "detail": response.text[:300]}
    data = response.json()
    return data if isinstance(data, dict) else {"status": "ok"}


@router.post("/tools/vector-retrieval")
def vector_retrieval(
    body: VectorRetrievalIn,
    user: AuthUser = Depends(get_current_user),
    agent: AgentTokenPayload = Depends(require_agent_token("VECTOR_RETRIEVAL")),
) -> dict:
    result = _langgraph("/run/vector-retrieval", {"query": body.query, "top_k": body.top_k})
    return result if result is not None else _accepted("VECTOR_RETRIEVAL", agent)


@router.post("/tools/graph-retrieval")
def graph_retrieval(
    body: GraphRetrievalIn,
    user: AuthUser = Depends(get_current_user),
    agent: AgentTokenPayload = Depends(require_agent_token("GRAPH_RETRIEVAL")),
) -> dict:
    # Read-only query templates with parameters — never user-built queries.
    result = _langgraph("/run/graph-retrieval", {"template": body.template, "params": body.params})
    return result if result is not None else _accepted("GRAPH_RETRIEVAL", agent)


@router.post("/tools/document-index")
def document_index(
    body: DocumentIndexIn,
    user: AuthUser = Depends(get_current_user),
    agent: AgentTokenPayload = Depends(require_agent_token("DOCUMENT_INDEX")),
) -> dict:
    try:
        document_uuid = str(uuid_mod.UUID(body.document_id))
    except ValueError:
        raise HTTPException(400, "document_id must be a UUID")
    row = db.fetch_one(
        "select id, title, language, status, created_at, updated_at"
        " from documents where id = %s",
        (document_uuid,),
    )
    if row is None:
        raise HTTPException(404, "Document not found")
    return {"status": "ok", "tool": "DOCUMENT_INDEX", "document": row}


@router.post("/tools/human-handoff")
def human_handoff(
    body: HumanHandoffIn,
    user: AuthUser = Depends(get_current_user),
    agent: AgentTokenPayload = Depends(require_agent_token("HUMAN_HANDOFF")),
) -> dict:
    try:
        conversation_uuid = str(uuid_mod.UUID(body.conversation_id))
    except ValueError:
        conversation_uuid = None  # free-form id (demo/CLI) — column stays NULL
    db.execute(
        "insert into review_cases (conversation_id, requested_by, question_summary,"
        " proposed_answer, risk_level, status)"
        " values (%s, %s, %s, %s, 'LOW', 'OPEN')",
        (conversation_uuid, user.id, body.reason, None),
    )
    log_event(
        user.id, user.roles[0] if user.roles else None,
        "HUMAN_HANDOFF_CREATED", "review_cases",
        metadata={"reason": body.reason[:200]},
    )
    return {"status": "ok", "tool": "HUMAN_HANDOFF", "review_case": "OPEN"}

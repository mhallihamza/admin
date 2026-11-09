# =====================================================================
# Client de la passerelle backend — contrat fixe utilisé par chaque
# acteur côté agent (flow 06 spécialistes, flow 08 handoff, flow 09 log).
#
# Deux étapes déterministes (le modèle ne COMPOSE JAMAIS le payload) :
#   1. POST {gateway_base_url}/api/gateway/token
#        body: {"agent","tool","operation":"execute","data_scope":"OWN"}
#        hdr : Authorization: Bearer <user_token>
#        -> le backend vérifie tool_permissions + agent_permissions et
#           renvoie un agent_token 60 s (refus audité, 403)
#   2. POST {gateway_base_url}/api/tools/<tool-slug>
#        hdr : Authorization: Bearer <user_token> + X-Agent-Token
# =====================================================================
from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT = 30.0


def tool_slug(tool: str) -> str:
    return tool.lower().replace("_", "-")


def token_payload(agent: str, tool: str) -> dict:
    return {"agent": agent, "tool": tool, "operation": "execute", "data_scope": "OWN"}


def _client(http: httpx.Client | None = None) -> httpx.Client:
    return http or httpx.Client(timeout=DEFAULT_TIMEOUT)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:500]}


def call_gateway_tool(
    session: dict[str, Any],
    agent: str,
    tool: str,
    payload: dict[str, Any],
    http: httpx.Client | None = None,
) -> dict:
    """Émet l'appel passerelle en 2 étapes. Retourne
    {"status": "ok"|"denied"|"error", "http_status": int, "body": ...}."""
    base = str(session.get("gateway_base_url", "")).rstrip("/")
    user_token = session.get("user_token", "")
    if not base or not user_token:
        return {"status": "error", "http_status": 0,
                "body": {"error": "gateway_base_url/user_token missing"}}

    try:
        client = _client(http)
        head = {"Authorization": f"Bearer {user_token}"}
        if session.get("agent_token"):
            agent_token = session["agent_token"]  # pré-émis (tests/pipeline)
        else:
            tok = client.post(f"{base}/api/gateway/token", json=token_payload(agent, tool), headers=head)
            if tok.status_code != 200:
                body = _safe_json(tok)
                return {"status": "denied" if tok.status_code == 403 else "error",
                        "http_status": tok.status_code, "body": body}
            agent_token = (tok.json() or {}).get("agent_token")
            if not agent_token:
                return {"status": "error", "http_status": tok.status_code,
                        "body": {"error": "no agent_token"}}

        result = client.post(f"{base}/api/tools/{tool_slug(tool)}",
                             json=payload,
                             headers={**head, "X-Agent-Token": agent_token})
        return {"status": "ok" if result.status_code == 200 else "denied",
                "http_status": result.status_code, "body": _safe_json(result)}
    except httpx.HTTPError as exc:
        return {"status": "error", "http_status": 0, "body": {"error": str(exc)[:200]}}


# -----------------------------------------------------------------------
# Payloads déterministes par outil (jamais composés par le modèle)
# -----------------------------------------------------------------------

def vector_payload(session: dict[str, Any]) -> dict:
    return {"query": str(session.get("question", ""))[:1000],
            "language": session.get("language", "fr"), "top_k": 6}


def graph_payload(session: dict[str, Any]) -> dict:
    return {"template": session.get("graph_template", "procedure_requirements"),
            "params": session.get("graph_params", {})}


def document_index_payload(session: dict[str, Any]) -> dict:
    return {"document_id": session.get("document_id", "")}


def handoff_payload(session: dict[str, Any]) -> dict:
    return {"conversation_id": session.get("conversation_id", ""),
            "reason": str(session.get("question_summary", session.get("question", "")))[:500]}

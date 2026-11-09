# =====================================================================
# Execution logging (flow 09) : POST /api/logs/execution du backend —
# écrit dans audit_events (action WORKFLOW_EXECUTION, moniteur admin
# /admin/workflows). Aucun token agent requis (comme le flow Langflow).
# =====================================================================
from __future__ import annotations

import httpx

from ..tracing import mark_start, record_timing


def log_execution(session: dict, flow: str, status: str, duration_ms: int,
                  correlation_id: str = "", http=None) -> dict:
    base = str(session.get("gateway_base_url", "")).rstrip("/")
    user_token = session.get("user_token", "")
    if not base or not user_token:
        return {"status": "failed", "http_status": 0, "body": {"error": "gateway_base_url/user_token missing"}}
    if status not in ("SUCCESS", "ERROR", "RUNNING"):
        return {"status": "failed", "http_status": 0, "body": {"error": f"invalid status {status!r}"}}
    try:
        client = http or httpx.Client(timeout=15)
        response = client.post(
            f"{base}/api/logs/execution",
            json={"flow": str(flow)[:120], "status": status,
                  "duration_ms": max(0, int(duration_ms)),
                  "correlation_id": str(correlation_id)[:64]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        body = {}
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:300]}
        return {"status": "logged" if response.status_code in (200, 201) else "failed",
                "http_status": response.status_code, "body": body}
    except httpx.HTTPError as exc:
        return {"status": "failed", "http_status": 0, "body": {"error": str(exc)[:200]}}


def node_log_execution(state: dict) -> dict:
    started = mark_start()
    session = dict(state.get("session") or {})
    timings = state.get("node_timings") or []
    duration_ms = max((t.get("ms", 0) for t in timings), default=0)
    inject = state.get("_inject") or {}
    outcome = log_execution(
        session,
        flow=session.get("flow", "guide-graph/chat-pipeline"),
        status=session.get("execution_status", "SUCCESS"),
        duration_ms=int(session.get("duration_ms", duration_ms)),
        correlation_id=state.get("request_id", ""),
        http=inject.get("http"),
    )
    return {**record_timing(state, "log_execution", started), "execution": outcome}


def build_execution_log_graph():
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("log_execution", node_log_execution)
    builder.add_edge(START, "log_execution")
    builder.add_edge("log_execution", END)
    return builder.compile()


def run_execution_log(session: dict, flow: str, status: str, duration_ms: int,
                      correlation_id: str = "", http=None) -> dict:
    return log_execution(session, flow, status, duration_ms, correlation_id, http=http)

# =====================================================================
# Human review handoff (flow 08) : via la passerelle (outil
# HUMAN_HANDOFF, agent SUPERVISOR) — token agent 60 s puis
# POST /api/tools/human-handoff → le backend crée le review_case
# (statut OPEN) visible dans la file employé.
# =====================================================================
from __future__ import annotations

from ..tools import gateway_client
from ..tracing import mark_start, record_timing

TOOL = "HUMAN_HANDOFF"
AGENT = "SUPERVISOR"


def run_handoff(session: dict, http=None) -> dict:
    return gateway_client.call_gateway_tool(
        session, AGENT, TOOL, gateway_client.handoff_payload(session), http=http)


def node_handoff(state: dict) -> dict:
    started = mark_start()
    session = dict(state.get("session") or {})
    if not session.get("gateway_base_url"):
        from .. import config

        session.setdefault("gateway_base_url", config.BACKEND_GATEWAY_URL)
    outcome = run_handoff(session, http=(state.get("_inject") or {}).get("http"))
    status = "handed_off" if outcome.get("status") == "ok" else outcome.get("status", "failed")
    return {**record_timing(state, "handoff", started),
            "handoff_result": {"status": status,
                               "http_status": outcome.get("http_status", 0),
                               "body": outcome.get("body", {})}}


def build_handoff_graph():
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("handoff", node_handoff)
    builder.add_edge(START, "handoff")
    builder.add_edge("handoff", END)
    return builder.compile()


def run_handoff_flow(session: dict, http=None) -> dict:
    return build_handoff_graph().invoke({"session": dict(session or {}),
                                         "_inject": {"http": http}})["handoff_result"]

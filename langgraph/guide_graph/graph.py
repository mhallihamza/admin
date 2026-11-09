# =====================================================================
# Graphes du Guide Administratif — deux modes d'exécution (comme le
# layout Langflow "flow 01 chaîne vers flow 06 sur ALLOW") :
#
#   • gate (POST /run/security-gate) :
#       layer1 → layer2 → decide → (log_and_stop)? → END
#
#   • chat (POST /run/pipeline) — pipeline de réponse complète :
#       gate → (ALLOW) → supervisor → validate → log_execution → END
#                     \-> (REVIEW/RESTRICT/BLOCK) → log_and_stop → END
#       réponse non validée (flow 07) → hold_answer → log_and_stop
#
# plus les graphes autonomes : ingestion (02), population (03),
# retrieval (04), graph_retrieval (05), handoff (08), log (09).
# =====================================================================
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .nodes import (execution_log, gate, graph_retrieval, handoff,
                    ingestion, output_filter, population, retrieval, supervisor,
                    validation)
from .state import WorkflowState


def _detected_layer2(state: WorkflowState) -> dict:
    """Wrapper qui injecte le détecteur (réel ou de test) depuis _inject."""
    return gate.run_layer2(state, detector=(state.get("_inject") or {}).get("detector"))


# ---------------------------------------------------------------------------
# Graphe maître "chat" : gate → supervisor → validation → log
# ---------------------------------------------------------------------------
def _route_after_gate(state: WorkflowState) -> str:
    if state.get("gate_decision", "ALLOW") == "ALLOW":
        return "supervisor"
    return "log_and_stop"


def _route_after_validate(state: WorkflowState) -> str:
    if (state.get("validation") or {}).get("valid", False):
        return "log"
    # Réponse non validée : retenue → REVIEW ; le BACKEND bloque la réponse.
    return "hold_answer"


def _route_after_output_filter(state: WorkflowState) -> str:
    if (state.get("output_filter") or {}).get("safe", False):
        return "validate"
    return "hold_answer"


def _hold_answer(state: WorkflowState) -> dict:
    return {
        "gate_decision": "REVIEW",
        "answer_final": None,
        "gate_reason": (state.get("gate_reason")
                        or (state.get("output_filter") or {}).get("reason")
                        or "Answer failed the final safety filter — held for review."),
    }


def _collect_chunks(state: WorkflowState) -> dict:
    """Pont déterministe spécialistes → flow 07 : les chunks approuvés
    renvoyés par la passerelle (VECTOR_RETRIEVAL) alimentent la
    validation des citations. Aucun modèle ici."""
    results = state.get("gateway_results") or {}
    body = (results.get("VECTOR_RETRIEVAL") or {}).get("body") or {}
    chunks = body.get("results") or body.get("chunks") or []
    records = ((results.get("GRAPH_RETRIEVAL") or {}).get("body") or {}).get("records") or []
    return {"chunks_meta": list(chunks), "graph_records": list(records)}


def build_chat_graph() -> Any:
    builder = StateGraph(WorkflowState)
    # flow 01
    builder.add_node("layer1", gate.run_layer1)
    builder.add_node("layer2", _detected_layer2)
    builder.add_node("decide", gate.compute_decision)
    # flow 06
    builder.add_node("classify", supervisor.node_classify)
    for specialist in supervisor.SPECIALISTS:
        builder.add_node(f"specialist_{specialist.lower()}",
                         supervisor.node_specialist(specialist))
    # pont déterministe chunks passerelle -> flow 07
    builder.add_node("collect", _collect_chunks)
    # flow 07b final leakage/safety filter
    builder.add_node("output_filter", output_filter.node_output_filter)
    # flow 07
    builder.add_node("validate", validation.node_validate)
    builder.add_node("hold_answer", _hold_answer)
    # fin d'exécution : log incident (non-ALLOW) ou log d'exécution (flow 09)
    builder.add_node("log_and_stop", gate.log_and_stop)
    builder.add_node("log", execution_log.node_log_execution)

    builder.add_edge(START, "layer1")
    builder.add_edge("layer1", "layer2")
    builder.add_edge("layer2", "decide")
    builder.add_conditional_edges("decide", _route_after_gate,
                                  {"supervisor": "classify", "log_and_stop": "log_and_stop"})
    builder.add_conditional_edges("classify", supervisor.route_specialist,
                                  {s: f"specialist_{s.lower()}" for s in supervisor.SPECIALISTS})
    for specialist in supervisor.SPECIALISTS:
        builder.add_edge(f"specialist_{specialist.lower()}", "collect")
    builder.add_edge("collect", "output_filter")
    builder.add_conditional_edges("output_filter", _route_after_output_filter,
                                  {"validate": "validate", "hold_answer": "hold_answer"})
    builder.add_conditional_edges("validate", _route_after_validate,
                                  {"log": "log", "hold_answer": "hold_answer"})
    builder.add_edge("hold_answer", "log_and_stop")
    builder.add_edge("log", END)
    builder.add_edge("log_and_stop", END)
    return builder.compile()


def run_chat(payload: dict, session: dict, detector: gate.DetectorFn | None = None,
             http: Any | None = None, llm: Any | None = None) -> dict:
    state = build_chat_graph().invoke({
        "payload": payload, "session": dict(session or {}),
        "_inject": {"detector": detector, "http": http, "llm": llm},
    })
    return {
        "gate_decision": state.get("gate_decision"),
        "gate_reason": state.get("gate_reason"),
        "layer1_violations": state.get("layer1_violations", []),
        "layer2": {
            "connected": state.get("layer2_connected", False),
            "risk_level": state.get("layer2_risk", "LOW"),
            "attack_type": state.get("layer2_attack_type"),
            "confidence": state.get("layer2_confidence", 0.0),
            "reason": state.get("layer2_reason", ""),
        },
        "specialist": state.get("specialist"),
        "answer": state.get("answer_final"),
        "citations": state.get("citations", []),
        "validation": state.get("validation"),
        "output_filter": state.get("output_filter"),
        "incident": state.get("incident"),
        "logged": state.get("logged"),
        "execution": state.get("execution"),
        "request_id": state.get("request_id"),
        "node_timings": state.get("node_timings", []),
        "llm_usage": state.get("llm_usage", {"in": 0, "out": 0}),
    }


# ---------------------------------------------------------------------------
# Graphes autonomes (mêmes nœuds, exécution isolée — comme les flows
# Langflow 02-05, 08, 09 qui se lançaient individuellement)
# ---------------------------------------------------------------------------
def build_standalone_graphs() -> dict:
    """Tous les graphes exécutables du service (pour api.py / scripts)."""
    return {
        "gate": gate.build_gate_graph(),
        "chat": build_chat_graph(),
        "ingestion": ingestion.build_ingestion_graph(),
        "population": population.build_population_graph(),
        "retrieval": retrieval.build_retrieval_graph(),
        "graph_retrieval": graph_retrieval.build_graph_retrieval_graph(),
        "supervisor": supervisor.build_supervisor_graph(),
        "handoff": handoff.build_handoff_graph(),
        "execution_log": execution_log.build_execution_log_graph(),
    }

# =====================================================================
# Traces par nœud + compteur usage LLM (parité soukna : agent_timings).
# In-process, injecté dans l'état — le backend reste l'autorité
# d'écriture en base (audit_events via flow 09).
# =====================================================================
from __future__ import annotations

import time
from typing import Any


def mark_start() -> float:
    return time.perf_counter()


def record_timing(state: dict[str, Any], node: str, started: float) -> dict[str, Any]:
    """Accumule (node, ms) dans state['node_timings'] ; nudges request_id
    si absent. Retourne les clés à merger dans l'état."""
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    timings = list(state.get("node_timings") or [])
    timings.append({"node": node, "ms": elapsed_ms})
    out: dict[str, Any] = {"node_timings": timings}
    if not state.get("request_id"):
        import uuid

        out["request_id"] = f"wf-{uuid.uuid4().hex[:12]}"
    out["run_mode"] = state.get("run_mode") or node
    return out

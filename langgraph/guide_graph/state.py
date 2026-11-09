# =====================================================================
# État partagé des graphes Guide Administratif.
# Un TypedDict porte toute la requête citoyenne (gate → retrieval →
# spécialistes → validation → logging), comme les flows Langflow se
# transmettaient leurs JSON.
# =====================================================================
from __future__ import annotations

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    # --- flow 01: central security gate -------------------------------------
    payload: dict                       # gate request payload (backend-built)
    session: dict                       # question/language/tokens/conversation
    gate_decision: str                  # ALLOW | RESTRICT | REVIEW | BLOCK
    gate_reason: str                    # sanited (no GATE_DECISION marker)
    layer1_violations: list[dict[str, str]]
    layer2_connected: bool
    layer2_risk: str
    layer2_attack_type: str | None
    layer2_confidence: float
    layer2_reason: str
    incident: dict | None               # written for every non-ALLOW decision
    logged: bool
    log_error: str | None

    # --- flow 02: document ingestion -----------------------------------------
    raw_text: str
    ingestion_metadata: dict
    clean: dict                        # {"clean_text", "original_length", ...}
    security: dict                     # {"text_safe", "flags", ...}
    chunks: list[dict]                  # split articles (also reused by flow 04)
    ingestion_summary: dict

    # --- flow 03: graph population --------------------------------------------
    extraction: dict                    # {"entities": [...], "relations": [...],
                                        #  "rejected": [...]}
    write_summary: dict                 # {"written_entities": n, ...}

    # --- flow 04: vector retrieval ----------------------------------------------
    query: str
    dropped: int
    chunks_meta: list[dict]             # filtered APPROVED + current chunks
    criteria: dict                      # {"approval_status": ..., "is_current": ...}

    # --- flow 05: graph retrieval ---------------------------------------------------
    graph_template: str
    graph_params: dict
    graph_records: list[dict]
    graph_error: str | None

    # --- flow 06: supervisor + specialists ---------------------------------------------
    specialist: str                     # PROCEDURE | LEGAL_RESEARCH | DOCUMENT_ADMIN
    intent_reason: str
    gateway_results: dict               # {"VECTOR_RETRIEVAL": {...}, ...}
    answer: str                         # specialist answer (marker on line 1)

    # --- flow 07: answer validation --------------------------------------------------------
    citations: list[dict]
    validation: dict | None             # {"valid": bool, "invalid_citations": [...]}
    answer_final: str | None            # None when validation withheld the answer
    output_filter: dict | None          # final safety/leakage check before return

    # --- flow 08: human review handoff ------------------------------------------------------
    handoff_result: dict | None

    # --- flow 09: execution logging ----------------------------------------------------------
    execution: dict | None

    # --- observabilité (soukna-style per-request tracing) ------------------------------------
    request_id: str
    run_mode: str                       # gate | chat | ingestion | populate | ...
    node_timings: list[dict]
    llm_mode: str                       # mistral | heuristic (dernier agent LLM)
    llm_usage: dict[str, int]

    # --- in-memory injection (tests); never serialized to clients ------------------------------
    _inject: dict

# =====================================================================
# Nœuds du(nœuds) Central Security Gate (flow 01). Mêmes règles que le
# flow Langflow :
#   Layer 1 — règles Python fixes (aucun modèle, aucun outil)
#   Layer 2 — agent de détection (Mistral, sans outils, structured JSON)
#   La décision FINALE (ALLOW / RESTRICT / REVIEW / BLOCK) est prise
#   par ce code backend-side — jamais par le modèle.
#
# Fail-closed :
#   * payload illisible            -> BLOCK (PAYLOAD_INVALID)
#   * JSON Layer 2 malformé        -> REVIEW (DETECTOR_MALFORMED, jamais LOW)
#   * detector en erreur/injoignable -> REVIEW (DETECTOR_FAILURE)
#   * décision inconnue            -> tombe dans log_and_stop => BLOCK
# =====================================================================
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Literal

from .. import config, llm as llm_mod
from ..prompts import DETECTOR_PROMPT
from ..tools import incidents
from ..tracing import mark_start, record_timing

DetectorFn = Callable[[str], dict]

# ---------------------------------------------------------------------------
# Layer 1 — règles fixes (Python pur)
# ---------------------------------------------------------------------------
KNOWN_ROLES = {
    "VISITOR", "CITIZEN", "EMPLOYEE", "CONTENT_APPROVER",
    "SYSTEM_ADMIN", "SECURITY_AUDITOR", "PLATFORM_SUPER_ADMIN",
}
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

# --- SQLi évidente (jamais exécutée nulle part) ----------------------------
SQL_INJECTION_PATTERNS = [
    re.compile(r"'\s*;\s*(drop|delete|truncate|update|insert|alter)\b", re.I),
    re.compile(r"\b(drop|truncate|alter)\s+table\b", re.I),
    re.compile(r"\bunion\s+(all\s+)?select\b", re.I),
    re.compile(r"'\s*(or|and)\s+[^=\n]{0,20}\s*=", re.I),
    re.compile(r"\bexec(?:ute)?\s+(xp_|sp_|cmdshell)", re.I),
    re.compile(r"\b(sleep|benchmark|pg_sleep)\s*\(", re.I),
    re.compile(
        r"\bselect\b[^\n]{0,80}\bfrom\b[^\n]{0,40}\b(pg_catalog|information_schema|sysobjects)",
        re.I,
    ),
]

# --- Jetons de contrôle PPI --------------------------------------------------
PPI_CONTROL_PATTERNS = [
    re.compile(r"<\|[^|>]{1,40}\|>", re.I),
    re.compile(r"<<\s*system\s*>>", re.I),
    re.compile(r"\[\s*inst\s*\].{0,4000}\[\s*/inst\s*\]", re.I),
]


def _token_abuse_reason(text: str) -> str | None:
    """Flood/token-waste déterministe — ne censure pas l'usage normal."""
    if len(text) > 2000:
        return None  # SIZE_LIMIT déjà couvert
    from collections import Counter

    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]{2,}", text)
    if any(len(item) >= 512 for item in tokens):
        return "Encoded token payload exceeds the budget."
    if len(tokens) < 24:
        return None
    counts = Counter(token.casefold() for token in tokens)
    token, repeat = counts.most_common(1)[0]
    if repeat >= 25 and repeat / len(tokens) >= 0.5:
        return f"Token exhaustion pattern: {token!r} repeated {repeat} times."
    return None


def parse_payload(raw: Any) -> dict:
    """Parse strict du payload (le modèle ne le construit jamais) :
    dict ou chaîne JSON ; le reste échoue fermé."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def run_layer1(state: dict) -> dict:
    started = mark_start()
    payload = parse_payload(state.get("payload", ""))
    if not payload:
        return {
            "layer1_violations": [{"rule": "PAYLOAD_INVALID", "detail": "Payload unreadable — fail closed."}],
            **record_timing(state, "layer1", started),
        }
    violations: list[dict[str, str]] = []

    text = payload.get("text")
    if not isinstance(text, str):
        violations.append({"rule": "PAYLOAD_INVALID", "detail": "Field 'text' is missing or not a string."})

    user_id = payload.get("user_id")
    roles = payload.get("roles")
    request_type = payload.get("request_type")
    disabled = payload.get("disabled")
    filename = payload.get("filename")
    source_user_id = payload.get("source_user_id")
    agent = payload.get("agent")
    tool = payload.get("tool")
    agent_tool_allowed = payload.get("agent_tool_allowed")

    # LOGIN_STATE
    if not isinstance(user_id, str) or not user_id.strip():
        violations.append({"rule": "LOGIN_REQUIRED",
                           "detail": "Unauthenticated request for a protected operation."})

    # ROLE_VS_REQUEST + ROLE_STRUCTURE
    if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
        violations.append({"rule": "ROLE_STRUCTURE_INVALID", "detail": "roles must be an array of role strings."})
        roles = []
    elif any(r not in KNOWN_ROLES for r in roles):
        violations.append({"rule": "ROLE_STRUCTURE_INVALID", "detail": "Unknown role value."})
    if isinstance(user_id, str) and user_id.strip():
        if request_type == "chat" and "CITIZEN" not in roles:
            violations.append({"rule": "ROLE_VS_REQUEST", "detail": "Chat requires the CITIZEN role."})
        if request_type == "tool" and "VISITOR" in roles and len(roles) == 1:
            violations.append({"rule": "ROLE_VS_REQUEST", "detail": "VISITOR cannot invoke tools."})
    if disabled is True:
        violations.append({"rule": "ACCOUNT_DISABLED", "detail": "Account is disabled."})

    # REQUEST_TYPE
    if request_type not in ("chat", "tool", "upload"):
        violations.append({"rule": "REQUEST_TYPE_INVALID", "detail": f"Unknown request_type: {request_type!r}"})

    # SQL_INJECTION — ne JAMAIS laisser un payload SQL arriver au pipeline
    if isinstance(text, str):
        if any(pattern.search(text) for pattern in SQL_INJECTION_PATTERNS):
            violations.append({"rule": "SQL_INJECTION", "detail": "SQL-injection payload detected."})
        if any(pattern.search(text) for pattern in PPI_CONTROL_PATTERNS):
            violations.append({"rule": "PPI_CONTROL_TOKEN", "detail": "Prompt control tokens detected."})
        if abuse := _token_abuse_reason(text):
            violations.append({"rule": "TOKEN_ABUSE", "detail": abuse})

    # SIZE_LIMIT
    if isinstance(text, str) and len(text) > 2000:
        violations.append({"rule": "SIZE_LIMIT", "detail": "Text exceeds 2000 characters."})

    # FILE_TYPE
    if filename is not None:
        ext = str(filename).rsplit(".", 1)[-1].lower() if "." in str(filename) else ""
        if ext not in ALLOWED_EXTENSIONS:
            violations.append({"rule": "FILE_TYPE", "detail": f"File type not allowed: {ext or 'none'}"})

    # DATA_SCOPE / data_scope=ALL (never allowed)
    if source_user_id is not None and source_user_id != user_id:
        violations.append({"rule": "DATA_SCOPE", "detail": "Request targets another user's data."})
    if payload.get("data_scope") in {"ALL", "ALL_USERS", "OTHER"}:
        violations.append({"rule": "DATA_SCOPE", "detail": "Bulk data scope is not allowed."})
    operation = payload.get("operation")
    if operation and str(operation).lower() not in {"execute", "read", "list"}:
        violations.append({"rule": "OPERATION_NOT_ALLOWED",
                           "detail": f"Operation {operation!r} is not allowed."})

    # AGENT_ALLOWED — l'absence d'agent/tool n'est PAS une permission
    if (agent is not None or tool is not None) and agent_tool_allowed is not True:
        violations.append({"rule": "AGENT_NOT_ALLOWED",
                           "detail": f"Agent {agent!r} / tool {tool!r} not explicitly allowed."})

    return {
        "layer1_violations": violations,
        **record_timing(state, "layer1", started),
    }


# ---------------------------------------------------------------------------
# Layer 2 — détection (Mistral, pas d'outils, JSON structuré)
# ---------------------------------------------------------------------------
def _detector_chain(api_key: str):
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_mistralai import ChatMistralAI

    chain_llm = ChatMistralAI(
        model=config.MISTRAL_MODEL,          # plan-dependent (ex.: codestral-latest)
        temperature=0,
        api_key=api_key,
        timeout=30,
    )
    prompt = ChatPromptTemplate.from_messages([("system", DETECTOR_PROMPT), ("human", "{text}")])
    return prompt | chain_llm


def _parse_detector_json(raw: str) -> dict | None:
    return llm_mod.extract_json(str(raw))


def default_detector(text: str) -> dict:
    """Vrai détecteur de Layer 2 : objet JSON brut ou levée d'exception —
    l'appelant décide du comportement fail-closed. Deux tentatives au
    plus : une erreur ponctuelle de l'API (429/timeout) ne doit pas
    transformer une requête propre en REVIEW."""
    api_key = config.MISTRAL_API_KEY
    if not api_key:
        raise LookupError("MISTRAL_API_KEY not configured.")
    last_error: Exception | None = None
    parsed: dict | None = None
    for attempt in range(2):
        try:
            response = _detector_chain(api_key).invoke({"text": str(text)[:2000]})
            content = getattr(response, "content", "") or ""
            parsed = _parse_detector_json(content)
            if parsed is not None:
                return parsed
            last_error = ValueError("Detector returned non-JSON.")
        except Exception as exc:  # noqa: BLE001 — réessai avant fail-close
            last_error = exc
        if attempt == 0:
            time.sleep(2.0)
    raise last_error if last_error else RuntimeError("Detector failed.")


def detect_layer2(payload: dict, detector: DetectorFn | None = None) -> dict:
    """Sémantique du nœud layer2 : jamais ALLOW silencieux si le
    détecteur n'est pas fiable."""
    if detector is None:
        detector = default_detector
    text = payload.get("text", "")
    try:
        parsed = detector(text)
    except LookupError:
        return {"connected": False, "risk_level": "LOW", "attack_type": None,
                "confidence": 0.0,
                "reason": "Layer 2 detection agent not connected (no MISTRAL_API_KEY) — skipped."}
    except Exception:  # noqa: BLE001 — un détecteur en erreur n'ouvre PAS la porte
        return {"connected": True, "risk_level": "HIGH", "attack_type": "DETECTOR_FAILURE",
                "confidence": 0.5, "reason": "Detection agent unreachable — flagged for review."}

    risk = str(parsed.get("risk_level", "LOW")).upper()
    if risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return {"connected": True, "risk_level": "HIGH", "attack_type": "DETECTOR_MALFORMED",
                "confidence": 0.5, "reason": "Detector returned an unknown risk_level."}
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        return {"connected": True, "risk_level": "HIGH", "attack_type": "DETECTOR_MALFORMED",
                "confidence": 0.5, "reason": "Detector confidence unreadable."}
    reason = str(parsed.get("reason", ""))[:500].replace("GATE_DECISION", "[removed]")
    return {"connected": True, "risk_level": risk,
            "attack_type": parsed.get("attack_type"),
            "confidence": confidence, "reason": reason}


def run_layer2(state: dict, detector: DetectorFn | None = None) -> dict:
    started = mark_start()
    result = detect_layer2(parse_payload(state.get("payload", "")), detector=detector)
    return {**record_timing(state, "layer2", started),
            "layer2_connected": bool(result["connected"]),
            "layer2_risk": result["risk_level"],
            "layer2_attack_type": result["attack_type"],
            "layer2_confidence": float(result["confidence"]),
            "layer2_reason": result["reason"]}


# ---------------------------------------------------------------------------
# Décision centrale — code déterministe, le modèle ne décide JAMAIS
# ---------------------------------------------------------------------------
def compute_decision(state: dict) -> dict:
    violations = state.get("layer1_violations", [])
    risk = state.get("layer2_risk", "LOW")
    confidence = state.get("layer2_confidence", 0.0)
    connected = state.get("layer2_connected", False)

    if violations:
        return {"gate_decision": "BLOCK",
                "gate_reason": "; ".join(v["detail"] for v in violations)}
    if not connected:
        # Détecteur non configuré : Layer 1 seul décide (parité Phase 4).
        return {"gate_decision": "ALLOW", "gate_reason": "Layer 2 detector not connected — skipped."}
    if risk == "CRITICAL" or confidence >= 0.85:
        return {"gate_decision": "BLOCK",
                "gate_reason": state.get("layer2_reason", "CRITICAL risk from Layer 2.")}
    if risk == "HIGH" or confidence >= 0.60:
        return {"gate_decision": "REVIEW",
                "gate_reason": state.get("layer2_reason", "HIGH risk from Layer 2.")}
    if risk == "MEDIUM":
        return {"gate_decision": "RESTRICT", "gate_reason": "MEDIUM risk — restricted capabilities."}
    return {"gate_decision": "ALLOW", "gate_reason": state.get("layer2_reason", "")}


def route_on_decision(state: dict) -> Literal["log_and_stop", "__end__"]:
    if state.get("gate_decision", "ALLOW") == "ALLOW":
        return "__end__"
    return "log_and_stop"


def route_after_layer1(state: dict) -> Literal["layer2", "decide"]:
    """Parité flow 01 Langflow : le détecteur n'est consulté que si la
    couche 1 est propre — un L1 déjà bloquant n'a pas besoin de L2."""
    return "decide" if state.get("layer1_violations") else "layer2"


def log_and_stop(state: dict) -> dict:
    """-terminal pour toute décision non-ALLOW. Écrit l'incident dans
    security_incidents (+ marqueur audit SECURITY_GATE_STOPPED). Un
    échec d'écriture ne change JAMAIS la décision prise."""
    started = mark_start()
    decision = state.get("gate_decision", "BLOCK")
    if decision not in ("BLOCK", "REVIEW", "RESTRICT"):
        decision = "BLOCK"  # inconnu => ferme
    layer1_attack = "GATE_LAYER1" if state.get("layer1_violations") else None
    attack_type = state.get("layer2_attack_type") or layer1_attack
    if attack_type not in {"PROMPT_INJECTION", "ROLE_ESCALATION", "DATA_EXFILTRATION",
                           "MALICIOUS_FILE", "RATE_ABUSE", "GATE_LAYER1"}:
        attack_type = "GATE_LAYER1"
    risk = state.get("layer2_risk", "LOW")
    incident = {
        "user_id": parse_payload(state.get("payload", "")).get("user_id"),
        "attack_type": attack_type,
        "risk_level": "HIGH" if (decision == "BLOCK" or risk in ("HIGH", "CRITICAL")) else "MEDIUM",
        "decision": decision,
        "reason": state.get("gate_reason", ""),
    }
    logged, log_error = incidents.log_security_incident(incident)
    return {**record_timing(state, "log_and_stop", started),
            "gate_decision": decision, "incident": incident,
            "logged": logged, "log_error": log_error}


# ---------------------------------------------------------------------------
# Construction du graphe (LangGraph)
# ---------------------------------------------------------------------------
def build_gate_graph(detector: DetectorFn | None = None):
    from langgraph.graph import END, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("layer1", run_layer1)
    builder.add_node("layer2", lambda s: run_layer2(s, detector=detector))
    builder.add_node("decide", compute_decision)
    builder.add_node("log_and_stop", log_and_stop)

    builder.set_entry_point("layer1")
    builder.add_conditional_edges("layer1", route_after_layer1,
                                  {"layer2": "layer2", "decide": "decide"})
    builder.add_edge("layer2", "decide")
    builder.add_conditional_edges("decide", route_on_decision,
                                  {"__end__": END, "log_and_stop": "log_and_stop"})
    builder.add_edge("log_and_stop", END)
    return builder.compile()


def run_gate(payload: dict | str, detector: DetectorFn | None = None) -> dict:
    """Exécute le gate en one-shot. Retourne l'état final complet."""
    graph = build_gate_graph(detector)
    return graph.invoke({
        "payload": payload if isinstance(payload, dict) else str(payload),
        "session": {},
    })

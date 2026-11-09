"""Central Security Gate.

Layer 1 — fixed, deterministic Python rules (no model):
  * login state vs request type
  * role vs request type (visitors cannot chat; citizens cannot call tools)
  * size limits
  * file type (when a filename is involved)
  * access to another user's data
  * allowed agent for the operation (via the permission tables)

Layer 2 — detection agent (LangGraph workflows, Phase 5): structured JSON
with risk level, attack type, confidence and reason. When MISTRAL_API_KEY
is not configured the layer is skipped with an explicit placeholder.

The FINAL decision (allow / restrict / review / block) is made here, by
this backend code — never by the model. Every non-allow decision is
recorded in security_incidents.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from . import permissions
from .auth import AuthUser
from .uploads import extension_of

BLOCK = "BLOCK"
REVIEW = "REVIEW"
RESTRICT = "RESTRICT"
ALLOW = "ALLOW"

# --- Obvious SQL injection markers (not executed anywhere) --------------
SQL_INJECTION_PATTERNS = [
    re.compile(r"'\s*;\s*(drop|delete|truncate|update|insert|alter)\b", re.I),
    re.compile(r"\b(drop|truncate|alter)\s+table\b", re.I),
    re.compile(r"\bunion\s+(all\s+)?select\b", re.I),
    re.compile(r"'\s*(or|and)\s+[^=\n]{0,20}\s*=", re.I),
    re.compile(r"\bexec(?:ute)?\s+(xp_|sp_|cmdshell)", re.I),
    re.compile(r"\b(sleep|benchmark|pg_sleep)\s*\(", re.I),
    re.compile(r"\bselect\b[^\n]{0,80}\bfrom\b[^\n]{0,40}\b(pg_catalog|information_schema|sysobjects)", re.I),
]

# --- Control tokens / machine-readable PPI -------------------------------
PPI_CONTROL_PATTERNS = [
    re.compile(r"<\|[^|>]{1,40}\|>", re.I),           # <|im_start|>
    re.compile(r"<<\s*system\s*>>", re.I),
    re.compile(r"\[\s*inst\s*\].{0,4000}\[\s*/inst\s*\]", re.I),  # [INST]…[/INST]
]

def _token_abuse_reason(text: str) -> str | None:
    """Cheap, deterministic DoS/token-waste detection (no model needed).
    Does NOT censor ordinary repeated words."""
    if len(text) > 2000:
        return None  # already caught by SIZE_LIMIT
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]{2,}", text)
    if any(len(item) >= 512 for item in tokens):
        return "Encoded token payload exceeds the budget."
    if len(tokens) < 24:
        return None
    counts = Counter(t.casefold() for t in tokens)
    token, repeat = counts.most_common(1)[0]
    if repeat >= 25 and repeat / len(tokens) >= 0.5:
        return f"Token exhaustion pattern: {token!r} repeated {repeat} times."
    if any(len(item) >= 512 for item in tokens):
        return "Encoded token payload exceeds the budget."
    return None


@dataclass
class GateVerdict:
    decision: str
    layer1_violations: list[dict[str, str]] = field(default_factory=list)
    layer2: dict[str, Any] | None = None
    reason: str = ""


def _layer1_rules(payload, user: AuthUser | None) -> list[dict[str, str]]:
    """Fixed rules. Each violation carries a rule id and explanation.
    Optional payload fields (agent, tool, filename, source_user_id) are
    read defensively so callers with narrower payloads still work."""
    violations: list[dict[str, str]] = []

    # 1) Login state vs request type: chat/tool/upload require a session.
    if user is None:
        violations.append(
            {"rule": "LOGIN_REQUIRED", "detail": "Unauthenticated request for a protected operation."}
        )
        return violations

    # 2) Role vs request type.
    if payload.request_type == "chat" and "CITIZEN" not in user.roles:
        violations.append(
            {"rule": "ROLE_VS_REQUEST", "detail": "Chat requires the CITIZEN role."}
        )
    if payload.request_type == "tool" and user.has_any_role("VISITOR"):
        violations.append(
            {"rule": "ROLE_VS_REQUEST", "detail": "VISITOR role cannot invoke tools."}
        )
    if user.disabled:
        violations.append({"rule": "ACCOUNT_DISABLED", "detail": "Account is disabled."})

    # 3) SQL-injection-like content in the prompt (never reaches the pipeline).
    if SQL_INJECTION_PATTERNS and any(p.search(payload.text) for p in SQL_INJECTION_PATTERNS):
        violations.append({"rule": "SQL_INJECTION", "detail": "SQL-injection payload detected."})

    # 3b) Machine-readable PPI/control-token markers in the prompt.
    if any(p.search(payload.text) for p in PPI_CONTROL_PATTERNS):
        violations.append({"rule": "PPI_CONTROL_TOKEN", "detail": "Prompt control tokens detected."})

    # 3c) Token/resource-waste patterns (deterministic, cheap).
    if abuse := _token_abuse_reason(payload.text):
        violations.append({"rule": "TOKEN_ABUSE", "detail": abuse})

    # 3d) Size limits (text payload).
    if len(payload.text) > 2000:
        violations.append({"rule": "SIZE_LIMIT", "detail": "Text payload exceeds 2000 characters."})

    # 4) File type, when a filename is involved.
    filename = getattr(payload, "filename", None)
    if filename:
        if extension_of(filename) not in {"pdf", "docx", "txt"}:
            violations.append({"rule": "FILE_TYPE", "detail": "File type not allowed."})

    # DATA_SCOPE / data_scope=ALL (never allowed)
    source_user_id = getattr(payload, "source_user_id", None)
    if source_user_id and source_user_id != user.id:
        violations.append(
            {"rule": "DATA_SCOPE", "detail": "Request targets another user's data."}
        )
    if getattr(payload, "data_scope", None) in {"ALL", "ALL_USERS", "OTHER"}:
        violations.append(
            {"rule": "DATA_SCOPE", "detail": "Bulk data scope is not allowed."}
        )
    operation = getattr(payload, "operation", None)
    if operation and operation.lower() not in {"execute", "read", "list"}:
        violations.append(
            {"rule": "OPERATION_NOT_ALLOWED",
             "detail": f"Operation {operation!r} is not allowed."}
        )

    # 6) Allowed agent for the operation (permission tables).
    agent = getattr(payload, "agent", None)
    tool = getattr(payload, "tool", None)
    if agent and tool:
        role_allowed = any(
            permissions.tool_permission_allowed(role, tool, "execute", "OWN")
            for role in user.roles
        )
        agent_allowed = permissions.agent_permission_allowed(agent, tool, "execute")
        if not (role_allowed and agent_allowed):
            violations.append(
                {
                    "rule": "AGENT_NOT_ALLOWED",
                    "detail": f"Agent {agent} / role not allowed for tool {tool}.",
                }
            )

    return violations


def _layer2_detection(payload, user: AuthUser | None) -> dict[str, Any]:
    """Detection agent (no tools) returning structured JSON. Runs in the
    standalone LangGraph workflow service (langgraph/api.py, /run/detect) —
    the same HTTP contract the Langflow flow 01 used to expose. Fail-closed:
    a transport error NEVER silently allows; it returns a HIGH/REVIEW signal.
    Never decides — the final decision stays in this code.

    When LANGGRAPH_SECURITY_GATE_URL is unset (offline/dev) the layer is
    skipped with an explicit placeholder, mirroring the old Langflow
    placeholder semantics."""
    import httpx

    from .config import get_settings

    settings = get_settings()
    url = settings.langgraph_security_gate_url
    if not url:
        return {
            "connected": False,
            "risk_level": "LOW",
            "attack_type": None,
            "confidence": 0.0,
            "reason": "Layer 2 detection agent not connected (LANGGRAPH_SECURITY_GATE_URL unset) — skipped.",
        }

    try:
        headers = {}
        if settings.langgraph_flow_token:
            headers["X-Flow-Token"] = settings.langgraph_flow_token

        response = httpx.post(
            url,
            json={
                "text": payload.text,
                "request_type": payload.request_type,
                "user_id": user.id if user else None,
                "filename": getattr(payload, "filename", None),
            },
            headers=headers,
            timeout=30.0,
        )
        result = response.json() if response.status_code == 200 else {}
        if response.status_code != 200 or not isinstance(result, dict) or not result:
            return {
                "connected": True,
                "risk_level": "HIGH",
                "attack_type": "DETECTOR_FAILURE",
                "confidence": 0.5,
                "reason": f"Detection service returned HTTP {response.status_code} — flagged for review.",
            }
    except (httpx.HTTPError, ValueError):
        return {
            "connected": True,
            "risk_level": "HIGH",
            "attack_type": "DETECTOR_FAILURE",
            "confidence": 0.5,
            "reason": "Detection agent unreachable — flagged for review.",
        }

    return {
        "connected": bool(result.get("connected")),
        "risk_level": str(result.get("risk_level", "LOW")).upper(),
        "attack_type": result.get("attack_type"),
        "confidence": float(result.get("confidence", 0.0)),
        "reason": str(result.get("reason", ""))[:500],
    }


def _final_decision(verdict: GateVerdict) -> str:
    """Backend decision logic. Layer 1 violations are hard blocks.
    Layer 2 informs restrict/review/block — it can never override a clean
    Layer 1 into a block on its own, and can never *allow* anything that
    Layer 1 flagged."""
    if verdict.layer1_violations:
        return BLOCK

    layer2 = verdict.layer2 or {}
    risk = layer2.get("risk_level", "LOW")
    confidence = float(layer2.get("confidence", 0.0))

    if risk == "CRITICAL" or confidence >= 0.85:
        return BLOCK
    if risk == "HIGH" or confidence >= 0.60:
        return REVIEW
    if risk == "MEDIUM":
        return RESTRICT
    return ALLOW


def run_security_gate(payload, user: AuthUser | None) -> GateVerdict:
    verdict = GateVerdict(decision=ALLOW)
    verdict.layer1_violations = _layer1_rules(payload, user)
    verdict.layer2 = _layer2_detection(payload, user)
    verdict.decision = _final_decision(verdict)

    if verdict.decision == BLOCK and verdict.layer1_violations:
        verdict.reason = "; ".join(v["detail"] for v in verdict.layer1_violations)
    elif verdict.layer2:
        verdict.reason = verdict.layer2.get("reason", "")
    return verdict

# =====================================================================
# Output Safety Filter — nœud FINAL de sécurité (flow 06b).
# Déterministe par défaut + juge LLM optionnel. Bloque (FAIL-CLOSED) :
#   • clés API / .env / secrets
#   • instructions internes / prompt système
#   • JSON d'outil / routing markers
#   • données privées non publiques
# Ce filtre s'applique APRÈS que le spécialiste a répondu et AVANT que
# le backend renvoie le texte au citoyen.
# =====================================================================
from __future__ import annotations

import re
from typing import Any, Callable

from .. import llm as llm_mod
from ..llm import make_llm
from ..prompts import OUTPUT_FILTER_PROMPT
from ..tracing import mark_start, record_timing

OutputDetectorFn = Callable[[str], dict]

# --- Déterministe : filtrer sans modèle, toujours actif -----------------
_HARD_PATTERNS = [
    (re.compile(r"(SUPABASE_(SERVICE_ROLE_KEY|SECRET_KEY|ANON_KEY)|MISTRAL_API_KEY|NEO4J_PASSWORD|AGENT_TOKEN_SECRET)\s*[=:]\s*\S+", re.I),
     "ENV_ASSIGNMENT"),
    (re.compile(r"(SERVICE_ROLE_KEY|ANON_KEY|AUTH_SECRET)\s*[=:]\s*\S+", re.I),
     "ENV_ASSIGNMENT"),
    (re.compile(r"(Bearer\s+eyJ[A-Za-z0-9_-]{12,}\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|x-agent-token\s*:?\s*\S{12,})", re.I),
     "AUTH_MATERIAL"),
    (re.compile(r"(?:^|[\s{\[])agent_token\s*[=:]\s*[\"']?[^\s,}]{8,}", re.I), "AGENT_TOKEN"),
    (re.compile(r"(?:^|[\s{\[])gateway_base_url\s*[=:]\s*https?://", re.I),
     "INTERNAL_ROUTE"),
    (re.compile(r"role\s*[:=]\s*[\"']?(SYSTEM_ADMIN|PLATFORM_SUPER_ADMIN|SECURITY_AUDITOR)[\"']?[^\n]{0,40}(password|token|jwt)", re.I),
     "CREDENTIAL_LEAK"),
    (re.compile(r"<\|(im_start|system|assistant)\|>", re.I), "CONTROL_TOKEN"),
    (re.compile(r"(?:^|[\s{\[])gateway_base_url\s*[=:]", re.I), "INTERNAL_ROUTE"),
    (re.compile(r"SUPABASE_SERVICE_ROLE_KEY|MISTRAL_API_KEY|NEO4J_PASSWORD|AGENT_TOKEN_SECRET", re.I), "SECRET_NAME"),
    (re.compile(r"(internal instruction|system prompt|prompt système|instructions système)", re.I),
     "INTERNAL_INSTRUCTION_MENTION"),
]


def scan_answer(answer: str) -> dict:
    findings: list[str] = []
    for pattern, label in _HARD_PATTERNS:
        if pattern.search(answer or ""):
            findings.append(label)
    return {
        "safe": not findings,
        "risk_level": "HIGH" if findings else "LOW",
        "findings": findings,
        "reason": "Output contains restricted/internal material." if findings else "",
    }


# --- Détecteur LLM (optionnel, avec fallback déterministe) -----------------
def default_output_detector(answer: str) -> dict:
    llm, _mode = make_llm(temperature=0.0, timeout=20.0)
    if llm is None:
        return scan_answer(answer)
    prompt = OUTPUT_FILTER_PROMPT.format(answer=str(answer)[:6000])
    ok, mode, _usage = llm_mod.call_llm_json(llm, prompt, fallback={})
    risk = str(ok.get("risk_level", "HIGH")).upper()
    if risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return {"safe": False, "risk_level": "HIGH",
                "findings": ["JUDGE_MALFORMED"],
                "reason": "Output judge returned an unknown risk_level."}
    safe = bool(ok.get("safe", risk == "LOW")) and risk == "LOW"
    return {
        "safe": safe,
        "risk_level": risk,
        "findings": [] if safe else ["JUDGE_" + risk],
        "reason": str(ok.get("reason", ""))[:500],
        "mode": mode,
    }


def run_output_filter(answer: str, detector: OutputDetectorFn | None = None) -> dict:
    if detector is None:
        detector = default_output_detector
    static = scan_answer(answer or "")
    if not static["safe"]:
        return static
    try:
        judged = detector(answer or "")
    except Exception:  # noqa: BLE001 — fail closed
        return {"safe": False, "risk_level": "HIGH",
                "findings": ["JUDGE_FAILURE"],
                "reason": "Output judge unreachable — answer withheld."}
    if not isinstance(judged, dict):
        return {"safe": False, "risk_level": "HIGH",
                "findings": ["JUDGE_MALFORMED"],
                "reason": "Output judge returned unreadable output."}
    risk = str(judged.get("risk_level", "HIGH")).upper()
    safe = bool(judged.get("safe", False)) and risk == "LOW"
    findings = judged.get("findings") or ([] if safe else ["JUDGE_" + (risk or "HIGH")])
    return {
        "safe": safe,
        "risk_level": risk if risk in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "HIGH",
        "findings": list(findings),
        "reason": str(judged.get("reason", ""))[:500],
    }


def node_output_filter(state: dict) -> dict:
    started = mark_start()
    answer = state.get("answer") or ""
    detector = (state.get("_inject") or {}).get("output_detector")
    verdict = run_output_filter(answer, detector=detector)
    return {
        **record_timing(state, "output_filter", started),
        "output_filter": verdict,
    }

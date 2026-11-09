"""Public chat (visitors without an account).

POST /api/chat/public — anonymous questions answered from APPROVED official
documents only (public information by nature):
  1. IP rate limit (abuse control),
  2. Layer 2 detection (prompt injection etc.) via the workflow service,
  3. grounded answer + deterministic citation validation (fail-closed).

No user data, no gateway tokens, no personalization: the retrieval corpus
is the public, APPROVED document set. Non-allow decisions are audited."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request

from .. import db
from ..audit import log_incident
from ..config import get_settings
from ..rate_limit import rate_limiter
from ..validation import PublicChatIn

router = APIRouter(prefix="/api", tags=["public-chat"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _layer2(text: str, ip: str) -> dict:
    """Détection Layer 2 via le service workflow (comme le gate)."""
    settings = get_settings()
    if not settings.langgraph_security_gate_url:
        return {"connected": False, "risk_level": "LOW", "attack_type": None,
                "confidence": 0.0, "reason": "detection not configured"}
    headers = {}
    if settings.langgraph_flow_token:
        headers["X-Flow-Token"] = settings.langgraph_flow_token
    try:
        response = httpx.post(
            settings.langgraph_security_gate_url,
            json={"text": text[:2000], "request_type": "chat",
                  "user_id": f"public:{ip}", "filename": None},
            headers=headers, timeout=30.0,
        )
        data = response.json()
        return {"connected": True, "risk_level": str(data.get("risk_level", "LOW")).upper(),
                "attack_type": data.get("attack_type"),
                "confidence": float(data.get("confidence", 0.0)),
                "reason": str(data.get("reason", ""))[:300]}
    except (httpx.HTTPError, ValueError):
        # détecteur injoignable : fail-closed côté décision
        return {"connected": True, "risk_level": "HIGH",
                "attack_type": "DETECTOR_FAILURE", "confidence": 0.5,
                "reason": "Detection agent unreachable."}


def _public_answer(question: str, language: str) -> dict:
    settings = get_settings()
    headers = {}
    if settings.langgraph_flow_token:
        headers["X-Flow-Token"] = settings.langgraph_flow_token
    response = httpx.post(
        f"{settings.langgraph_base_url.rstrip('/')}/run/public-answer",
        json={"question": question, "language": language},
        headers=headers, timeout=300.0,
    )
    response.raise_for_status()
    return response.json()


@router.post("/chat/public")
def public_chat(payload: PublicChatIn, request: Request) -> dict:
    settings = get_settings()
    ip = _client_ip(request)
    rate_limiter.check(f"public-chat:{ip}", settings.rate_limit_chat_per_min)

    text = payload.text.strip()
    layer2 = _layer2(text, ip)

    if layer2["risk_level"] in ("HIGH", "CRITICAL") or layer2["confidence"] >= 0.85:
        decision = "BLOCK" if layer2["confidence"] >= 0.85 or layer2["risk_level"] == "CRITICAL" else "REVIEW"
        log_incident(
            user_id=None, source_ip=ip,
            attack_type=layer2["attack_type"] or "GATE_LAYER1",
            risk_level="HIGH", decision=decision, reason=layer2["reason"],
            metadata={"public": True,
                      "route": str(request.url.path),
                      "flagged_text": text},
        )
        return {"decision": decision.lower(),
                "detail": "Votre message a été bloqué par le filtre de sécurité."}

    if not settings.langgraph_base_url:
        return {"decision": "unavailable",
                "detail": "Le service de réponse n'est pas encore connecté."}

    try:
        result = _public_answer(text, payload.language)
    except (httpx.HTTPError, ValueError):
        return {"decision": "unavailable",
                "detail": "Service de réponse momentanément indisponible — réessayez."}

    decision = str(result.get("decision", "review"))
    if decision == "allow":
        return {"decision": "allow", "answer": result.get("answer"),
                "citations": result.get("citations", [])}
    return {"decision": decision,
            "detail": result.get("detail") or "Réponse retenue pour vérification."}

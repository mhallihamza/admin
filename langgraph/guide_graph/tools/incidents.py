# =====================================================================
# Incidents sécurité — le gate (flow 01) écrit directement dans les
# tables Supabase via REST (comme le flow Langflow le faisait), avec la
# service-role key côté serveur. Un échec d'écriture NE CHANGE JAMAIS la
# décision déjà prise.
# =====================================================================
from __future__ import annotations

import json
from typing import Any

import requests

from .. import config


def log_security_incident(incident: dict[str, Any]) -> tuple[bool, str | None]:
    """POST security_incidents puis audit_events (marqueur
    SECURITY_GATE_STOPPED). Retourne (logged, log_error)."""
    if not config.supabase_ready():
        return False, "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured"
    base = config.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        r = requests.post(
            f"{base}/rest/v1/security_incidents",
            json={
                "user_id": incident.get("user_id"),
                "attack_type": incident.get("attack_type") or "GATE_LAYER1",
                "risk_level": incident.get("risk_level", "HIGH"),
                "decision": incident.get("decision", "BLOCK"),
                "reason": incident.get("reason", ""),
            },
            headers=headers,
            timeout=15,
        )
        if r.status_code not in (200, 201, 204):
            return False, f"security_incidents {r.status_code}"
        audit_payload = {
            "actor_id": incident.get("user_id"),
            "action": "SECURITY_GATE_STOPPED",
            "entity": "security_incidents",
            "metadata": json.dumps({"decision": incident.get("decision", "BLOCK"),
                                    "reason": incident.get("reason", "")}),
        }
        try:
            requests.post(f"{base}/rest/v1/audit_events", json=audit_payload,
                          headers=headers, timeout=15)
        except requests.RequestException:
            pass  # marqueur best-effort, jamais bloquant
        return True, None
    except requests.RequestException as exc:
        return False, str(exc)[:200]

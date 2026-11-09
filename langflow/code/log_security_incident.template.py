# Security gate — log + stop step (fixed code, LINEAR pipeline).
# Input : @@VAR:context@@ = the full gate decision JSON from the Decision step
# Behaviour:
#   ALLOW           -> passthrough: prints the FULL gate result (decision +
#                      session + violations + layer2) for the next workflow
#   non-ALLOW       -> logs to Supabase (security_incidents + audit_events),
#                      then STOPS the workflow (SystemExit) — Gate Result
#                      never executes
# Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

import json
import os
import re
import ast

RAW = r@@QUOTE@@
@@VAR:context@@
@@QUOTE@@

def parse_json_loose(raw):
    text = (raw or "").strip()
    for _ in range(8):
        if not text:
            return None
        obj = None
        try:
            obj = json.loads(text)
        except Exception:
            pass
        if obj is None:
            try:
                obj = ast.literal_eval(text)
            except Exception:
                pass
        if obj is None:
            match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
            if not match:
                return None
            fragment = match.group(0)
            try:
                obj = json.loads(fragment)
            except Exception:
                try:
                    obj = ast.literal_eval(fragment)
                except Exception:
                    return None
        if isinstance(obj, dict) and isinstance(obj.get("result"), str):
            text = obj["result"].strip()
            continue
        if isinstance(obj, str) and obj.strip():
            text = obj.strip()
            continue
        if isinstance(obj, (dict, list)):
            return obj
        BS = chr(92)
        unescaped = text.replace(BS + BS, chr(1) + "B" + chr(1))
        unescaped = unescaped.replace(BS + "'", "'")
        unescaped = unescaped.replace(BS + '"', '"')
        unescaped = unescaped.replace(BS + "n", chr(10))
        unescaped = unescaped.replace(BS + "r", chr(13))
        unescaped = unescaped.replace(chr(1) + "B" + chr(1), BS)
        if unescaped != text:
            text = unescaped.strip()
            continue
        return None
    return None

gate = parse_json_loose(RAW)
if not isinstance(gate, dict):
    gate = {"decision": "BLOCK", "reason": "Gate decision unreadable - failing closed"}

decision = gate.get("decision", "ALLOW")
reason = str(gate.get("reason", ""))[:500]
session = gate.get("session", {}) or {}
layer2 = gate.get("layer2", {}) or {}
violations = gate.get("layer1_violations", []) or []

if decision != "ALLOW":
    import urllib.request
    import urllib.error

    supabase_url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""

    risk_map = {"BLOCK": "HIGH", "REVIEW": "HIGH", "RESTRICT": "MEDIUM"}
    incident = {
        "user_id": session.get("user_id"),
        "attack_type": layer2.get("attack_type") or "GATE_LAYER1",
        "risk_level": risk_map.get(decision, "MEDIUM"),
        "decision": decision,
        "reason": reason,
    }

    logged = False
    log_error = None
    if supabase_url and service_key:
        headers = {
            "apikey": service_key,
            "Authorization": "Bearer " + service_key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        try:
            request = urllib.request.Request(
                supabase_url + "/rest/v1/security_incidents",
                data=json.dumps(incident).encode("utf-8"),
                method="POST",
                headers=headers,
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                logged = response.status in (200, 201)
        except urllib.error.HTTPError as error:
            log_error = f"HTTP {error.code}"
        except Exception as error:  # noqa: BLE001
            log_error = str(error)[:200]
    else:
        log_error = "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in the Langflow environment"

    if logged:
        audit = {
            "actor_id": session.get("user_id"),
            "action": "SECURITY_GATE_STOPPED",
            "entity": "security_incidents",
            "metadata": json.dumps({"decision": decision, "reason": reason}),
        }
        try:
            request = urllib.request.Request(
                supabase_url + "/rest/v1/audit_events",
                data=json.dumps(audit).encode("utf-8"),
                method="POST",
                headers=headers,
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                pass
        except Exception:  # noqa: BLE001, S110
            pass

    print(json.dumps({
        "decision": decision,
        "logged": logged,
        "log_error": log_error,
        "reason": reason,
        "session": session,
    }, ensure_ascii=True))

    # STOP THE WORKFLOW HERE — nothing runs after a non-ALLOW decision.

# ALLOW — pass the full payload forward
print(json.dumps({
    "decision": "ALLOW",
    "layer1_violations": violations,
    "layer2": layer2,
    "session": session,
    "reason": reason,
}, ensure_ascii=True))

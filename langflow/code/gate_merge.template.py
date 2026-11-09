# Central Security Gate — Central Decision (fixed deterministic code, the
# model NEVER decides).
# Inputs: layer1_json (Layer 1 result), layer2_text (Layer 2 raw output),
#         session_json (original session, forwarded unchanged)
# Output: line 1 = "GATE_DECISION: <decision>" (the routing marker consumed by
#         the conditional-router chain), line 2+ = full JSON.
# The reason text is sanitized so the model can never forge the marker.

import json
import re
import ast

LAYER1_RAW = r@@QUOTE@@
@@VAR:layer1_json@@
@@QUOTE@@

LAYER2_RAW = r@@QUOTE@@
@@VAR:layer2_text@@
@@QUOTE@@

SESSION_RAW = r@@QUOTE@@
@@VAR:session_json@@
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

layer1 = parse_json_loose(LAYER1_RAW)
if not isinstance(layer1, dict):
    layer1 = {"layer1_violations": [{"rule": "PAYLOAD_INVALID", "detail": "Layer 1 output unreadable - failing closed"}]}

layer2_raw = parse_json_loose(LAYER2_RAW)
if not isinstance(layer2_raw, dict):
    layer2 = {
        "risk_level": "HIGH",
        "attack_type": "DETECTOR_MALFORMED",
        "confidence": 0.5,
        "reason": "Detection model output missing or malformed - held for review.",
    }
else:
    layer2 = {
        "risk_level": str(layer2_raw.get("risk_level", "LOW")).upper(),
        "attack_type": layer2_raw.get("attack_type"),
        "confidence": float(layer2_raw.get("confidence", 0.0)),
        "reason": str(layer2_raw.get("reason", ""))[:500].replace("GATE_DECISION", "[removed]"),
    }

session = parse_json_loose(SESSION_RAW)
if not isinstance(session, dict):
    session = {}

# FINAL decision - fixed deterministic mapping. The model never decides.
violations = layer1.get("layer1_violations", [])
if violations:
    decision = "BLOCK"
    reason = "; ".join(str(v.get("detail", "")) for v in violations)[:500]
elif layer2["risk_level"] == "CRITICAL" or layer2["confidence"] >= 0.85:
    decision = "BLOCK"
    reason = layer2["reason"]
elif layer2["risk_level"] == "HIGH" or layer2["confidence"] >= 0.60:
    decision = "REVIEW"
    reason = layer2["reason"]
elif layer2["risk_level"] == "MEDIUM":
    decision = "RESTRICT"
    reason = layer2["reason"]
else:
    decision = "ALLOW"
    reason = layer2["reason"]

safe_reason = reason.replace("GATE_DECISION", "[removed]")

print("GATE_DECISION: " + decision)
print(json.dumps({
    "decision": decision,
    "layer1_violations": violations,
    "layer2": layer2,
    "session": session,
    "reason": safe_reason,
    "note": "non-ALLOW decisions are logged to the database by their branch step",
}, ensure_ascii=True))

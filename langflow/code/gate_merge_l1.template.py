# Security Gate — Layer 1 ONLY (no model, keyless testing variant).
# Input : @@VAR:layer1_json@@ = Layer 1 output JSON (printed by the Layer 1 interpreter)
# Output: printed JSON { layer1_violations, layer2: skipped, note }

import json
import re
import ast

RAW = r@@QUOTE@@
@@VAR:layer1_json@@
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

layer1 = parse_json_loose(RAW)
if not isinstance(layer1, dict):
    layer1 = {
        "layer1_violations": [{"rule": "PAYLOAD_INVALID", "detail": "merge parse failed"}],
        "raw_debug": RAW[:400],
    }

print(json.dumps({
    "layer1_violations": layer1.get("layer1_violations", []),
    "layer2": {"connected": False, "reason": "skipped in the keyless testing variant (01b)"},
    "note": "non-ALLOW decisions stop this workflow and are logged to the database by the next step",
}, ensure_ascii=True))

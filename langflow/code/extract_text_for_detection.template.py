# Security Gate — isolate ONLY the user text before any model sees it (fixed).
# Input : @@VAR:context@@ = full backend payload JSON (user_id, roles, text, ...)
# Output: printed JSON { "text": <user text only> }
# SECURITY: the Layer 2 model must NEVER see roles, user ids, permission flags
# or any other security-relevant field — those stay in the Python layers.

import json
import ast
import re

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
                    obj = None
        if isinstance(obj, dict) and isinstance(obj.get("result"), str):
            text = obj["result"].strip()  # unwrap the interpreter result key
            continue
        if isinstance(obj, str) and obj.strip():
            text = obj.strip()  # unwrap a string layer (repr of repr)
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






payload = parse_json_loose(RAW) or {}

print(json.dumps({"text": str(payload.get("text", ""))[:2000]}, ensure_ascii=True))

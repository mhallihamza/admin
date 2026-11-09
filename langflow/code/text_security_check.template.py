# Document ingestion — security check of the EXTRACTED text (deterministic).
# Input : @@VAR:context@@ = JSON from the clean-text step { clean_text, ... }
# Output: printed JSON { text_safe, flags[], cleaned_text }

import json
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

payload = parse_json_loose(RAW) or {"clean_text": RAW}

text = payload.get("clean_text") or ""
flags = []

patterns = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "INJECTION_IGNORE_INSTRUCTIONS"),
    (r"system\s*prompt", "INJECTION_PROMPT_DISCLOSURE"),
    (r"you\s+are\s+now\s+(a|an)\s+", "INJECTION_ROLE_OVERRIDE"),
    (r"<\|.*?\|>", "INJECTION_SPECIAL_TOKENS"),
]
for pattern, flag in patterns:
    if re.search(pattern, text, re.IGNORECASE):
        flags.append(flag)

if "\x00" in text:
    flags.append("BINARY_CONTENT")

print(json.dumps({
    "text_safe": len(flags) == 0,
    "flags": flags,
    "cleaned_text": text,
}, ensure_ascii=True))

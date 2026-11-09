# Answer validation — deterministic; NO model involved.
# Input : @@VAR:context@@ = JSON { citations: [ {document_id, article_number, version} ],
#                              chunks: [ retrieved chunks (filtered: APPROVED + current) ] }
# Output: printed JSON { valid, invalid_citations, checked_count }

import json
import ast
import re

INPUT_RAW = r@@QUOTE@@
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

payload = parse_json_loose(INPUT_RAW) or {}
citations = payload.get("citations", []) or []
chunks = payload.get("chunks", []) or []

known = set()
for chunk in chunks:
    metadata = chunk.get("metadata") or chunk
    known.add((
        str(metadata.get("document_id")),
        str(metadata.get("article_number")),
        str(metadata.get("version", "")),
        metadata.get("approval_status"),
        metadata.get("is_current"),
    ))

invalid = []
for citation in citations:
    found = any(
        k[0] == str(citation.get("document_id"))
        and k[1] == str(citation.get("article_number"))
        and k[2] == str(citation.get("version", ""))
        and k[3] == "APPROVED"
        and k[4] is not False
        for k in known
    )
    if not found:
        invalid.append(citation)

print(json.dumps({
    "valid": len(invalid) == 0 and len(citations) > 0,
    "invalid_citations": invalid,
    "checked_count": len(citations),
}, ensure_ascii=True))

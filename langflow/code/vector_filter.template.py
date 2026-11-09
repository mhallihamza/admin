# Vector retrieval — deterministic post-filter on approval status and version.
# Input : @@VAR:context@@ = JSON array of retrieved chunks (from the Astra DB search node)
# Output: printed JSON { results: [chunks], dropped, criteria }
# A chunk is kept ONLY if approval_status == APPROVED and it is the current version.

import json
import re

RAW = r@@QUOTE@@
@@VAR:context@@
@@QUOTE@@

def parse_any(raw):
    text = (raw or "").strip().replace("'''", '"\'"\'"')
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\[.*\]", text, re.DOTALL) or re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return []
    return []

payload = parse_any(RAW)
if isinstance(payload, dict):
    payload = payload.get("results") or payload.get("data") or []

results = []
dropped = 0
for chunk in payload:
    if not isinstance(chunk, dict):
        dropped += 1
        continue
    metadata = chunk.get("metadata") or chunk
    if metadata.get("approval_status") != "APPROVED":
        dropped += 1
        continue
    if metadata.get("is_current") is False:
        dropped += 1
        continue
    results.append(chunk)

print(json.dumps({
    "results": results,
    "dropped": dropped,
    "criteria": {"approval_status": "APPROVED", "is_current": True},
}, ensure_ascii=True))

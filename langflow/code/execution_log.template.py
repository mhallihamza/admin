# Execution logging — posts a workflow-execution record to the backend,
# which writes it into the audit_events table (WORKFLOW_EXECUTION).
# Input : @@VAR:context@@ = JSON { gateway_base_url, user_token,
#                              flow, status, duration_ms, correlation_id }
# Output: printed JSON { status, http_status, body }

import json
import ast
import re
from urllib.parse import urljoin

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






session = parse_json_loose(RAW) or {}

payload = {
    "flow": session.get("flow", ""),
    "status": session.get("status", "SUCCESS"),
    "duration_ms": session.get("duration_ms", 0),
    "correlation_id": session.get("correlation_id", ""),
}

import urllib.request
import urllib.error

base_url = (session.get("gateway_base_url") or "").rstrip("/") + "/"
url = urljoin(base_url, "api/logs/execution")
data = json.dumps(payload).encode("utf-8")
request = urllib.request.Request(url, data=data, method="POST", headers={
    "Content-Type": "application/json",
    "Authorization": "Bearer " + session.get("user_token", ""),
})

http_status = 0
body_text = ""
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        http_status = response.status
        body_text = response.read().decode("utf-8")
except urllib.error.HTTPError as error:
    http_status = error.code
    body_text = error.read().decode("utf-8", errors="replace")
except Exception as error:  # noqa: BLE001
    body_text = str(error)[:300]

try:
    body = json.loads(body_text)
except Exception:
    body = {"raw": body_text[:1000]}

print(json.dumps({"status": "logged" if http_status == 200 else "failed", "http_status": http_status, "body": body}, ensure_ascii=True))

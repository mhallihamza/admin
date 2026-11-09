# Gateway tool — parameterless from the agent's point of view. The payload is
# derived deterministically from the session, never composed by the model.
#   Step 1: POST /api/gateway/token with the USER token + (agent, tool) —
#           the backend checks tool_permissions + agent_permissions and
#           issues a short-lived agent token (60 s). Denials are audited.
#   Step 2: POST /api/tools/<tool> with BOTH tokens. The gateway
#           re-validates everything before executing.
# Input : @@VAR:session_json@@ = JSON { gateway_base_url, user_token, question,
#         language?, graph_template?, graph_params?, document_id? }
# Output: printed JSON { status, http_status, body }
#
# Constants injected per node: TOOL = @@TOOL@@, AGENT = @@AGENT@@

import json
import ast
import re
from urllib.parse import urljoin

TOOL = "@@TOOL@@"
AGENT = "@@AGENT@@"

RAW = r@@QUOTE@@
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

base_url = (session.get("gateway_base_url") or "").rstrip("/") + "/"
user_token = session.get("user_token") or ""

import urllib.request
import urllib.error

def http_json(url, body, headers, timeout=30):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")
    except Exception as error:  # noqa: BLE001
        return 0, str(error)[:300]

if not base_url.startswith("http") or not user_token:
    print(json.dumps({"status": "error", "http_status": 0, "body": "session missing (gateway_base_url / user_token)"}, ensure_ascii=True))

# Deterministic payload per tool — derived from the session, not from the model.
if TOOL == "VECTOR_RETRIEVAL":
    payload = {
        "query": (session.get("question") or "")[:1000],
        "language": session.get("language", "fr"),
        "top_k": 6,
    }
elif TOOL == "GRAPH_RETRIEVAL":
    payload = {
        "template": session.get("graph_template", "procedure_requirements"),
        "params": session.get("graph_params", {}),
    }
elif TOOL == "DOCUMENT_INDEX":
    payload = {"document_id": session.get("document_id", "")}
else:
    payload = {}

# --- Step 1: issue the short-lived agent token (backend checks permissions)
agent_token = session.get("agent_token") or ""
if not agent_token:
    token_status, token_text = http_json(
        urljoin(base_url, "api/gateway/token"),
        {"agent": AGENT, "tool": TOOL, "operation": "execute", "data_scope": "OWN"},
        {"Content-Type": "application/json", "Authorization": "Bearer " + user_token},
    )
    token_body = parse_json_loose(token_text) or {}
    if token_status != 200 or not token_body.get("agent_token"):
        print(json.dumps({"status": "denied", "http_status": token_status, "body": token_body or {"raw": token_text[:500]}}, ensure_ascii=True))
    agent_token = token_body["agent_token"]

# --- Step 2: call the tool through the gateway
tool_status, tool_text = http_json(
    urljoin(base_url, "api/tools/" + TOOL.lower().replace("_", "-")),
    payload,
    {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + user_token,
        "X-Agent-Token": agent_token,
    },
)

try:
    body = json.loads(tool_text)
except Exception:
    body = {"raw": tool_text[:1000]}

print(json.dumps({"status": "ok" if tool_status == 200 else "denied", "http_status": tool_status, "body": body}, ensure_ascii=True))

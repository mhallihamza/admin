# Central Security Gate — Layer 1 (fixed deterministic rules, no model, no tools)
# Input : @@VAR:context@@ = payload JSON built by the platform server from the
#         VERIFIED session token and its database (the citizen never posts it)
# Output: printed JSON { layer1_violations, checked }

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

parsed = parse_json_loose(RAW)
if not isinstance(parsed, dict):
    print(json.dumps({
        "layer1_violations": [{"rule": "PAYLOAD_INVALID",
                               "detail": "Layer 1 could not read the request payload - failing closed"}],
        "checked": [],
    }, ensure_ascii=True))

payload = parsed
violations = []
checked = []

text = payload.get("text")
if not isinstance(text, str):
    violations.append({"rule": "PAYLOAD_INVALID", "detail": "text field missing or not a string"})
    checked.append("PAYLOAD_STRUCTURE")

user_id = payload.get("user_id")
roles = payload.get("roles")
request_type = payload.get("request_type")
disabled = payload.get("disabled")

if not isinstance(user_id, str) or not user_id.strip():
    violations.append({"rule": "LOGIN_REQUIRED", "detail": "Unauthenticated request for a protected operation."})
checked.append("LOGIN_STATE")

KNOWN_ROLES = {"VISITOR", "CITIZEN", "EMPLOYEE", "CONTENT_APPROVER", "SYSTEM_ADMIN", "SECURITY_AUDITOR", "PLATFORM_SUPER_ADMIN"}
if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
    violations.append({"rule": "ROLE_STRUCTURE_INVALID", "detail": "roles must be an array of role strings."})
    roles = []
elif any(r not in KNOWN_ROLES for r in roles):
    violations.append({"rule": "ROLE_STRUCTURE_INVALID", "detail": "roles contain an unknown role value."})
if user_id and request_type == "chat" and "CITIZEN" not in roles:
    violations.append({"rule": "ROLE_VS_REQUEST", "detail": "Chat requires the CITIZEN role."})
if user_id and request_type == "tool" and "VISITOR" in roles and len(roles) == 1:
    violations.append({"rule": "ROLE_VS_REQUEST", "detail": "VISITOR role cannot invoke tools."})
if disabled is True:
    violations.append({"rule": "ACCOUNT_DISABLED", "detail": "Account is disabled."})
checked.append("ROLE_VS_REQUEST")

if request_type not in ("chat", "tool", "upload"):
    violations.append({"rule": "REQUEST_TYPE_INVALID", "detail": f"Unknown request_type: {request_type!r}"})
checked.append("REQUEST_TYPE")

if isinstance(text, str) and len(text) > 2000:
    violations.append({"rule": "SIZE_LIMIT", "detail": "Text payload exceeds 2000 characters."})
checked.append("SIZE_LIMIT")

filename = payload.get("filename")
if filename is not None:
    if not isinstance(filename, str) or "." not in filename:
        violations.append({"rule": "FILE_TYPE", "detail": "Filename missing or has no extension."})
    else:
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in {"pdf", "docx", "txt"}:
            violations.append({"rule": "FILE_TYPE", "detail": f"File type not allowed: {extension}"})
checked.append("FILE_TYPE")

source_user_id = payload.get("source_user_id")
if source_user_id is not None and source_user_id != user_id:
    violations.append({"rule": "DATA_SCOPE", "detail": "Request targets another user's data."})
checked.append("DATA_SCOPE")

agent = payload.get("agent")
tool = payload.get("tool")
if (agent is not None or tool is not None) and payload.get("agent_tool_allowed") is not True:
    violations.append({"rule": "AGENT_NOT_ALLOWED", "detail": f"Agent {agent!r} / tool {tool!r} not explicitly allowed."})
checked.append("AGENT_ALLOWED")

print(json.dumps({"layer1_violations": violations, "checked": checked}, ensure_ascii=True))

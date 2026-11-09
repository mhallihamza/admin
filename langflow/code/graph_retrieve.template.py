# Graph retrieval — FIXED read-only Cypher templates with bound parameters.
# Input : @@VAR:context@@ = JSON { template: <name from the list below>, params: {...} }
# Output: printed JSON { template, records: [...], params_used }
#
# SECURITY: queries are never built from user text. The template name selects a
# fixed query; values travel only as parameters; the session is READ-only.

import json
import ast
import os
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
template_name = str(payload.get("template", ""))
params = payload.get("params") or {}
if not isinstance(params, dict):
    params = {}

# Fixed read-only templates — the ONLY queries this flow can run.
TEMPLATES = {
    "procedure_requirements": (
        "MATCH (p:PROCEDURE {name: $procedure_name})-[:REQUIRES]->(d) "
        "RETURN d.name AS requirement LIMIT 50"
    ),
    "procedure_administration": (
        "MATCH (p:PROCEDURE {name: $procedure_name})-[:BELONGS_TO]->(a) "
        "RETURN a.name AS administration LIMIT 10"
    ),
    "documents_of_law": (
        "MATCH (l:LAW {name: $law_name})-[:PART_OF]->(d:DOCUMENT) "
        "RETURN d.name AS document LIMIT 50"
    ),
    "administration_services": (
        "MATCH (a:ADMINISTRATION {name: $administration_name})-[:MANAGED_BY|LOCATED_IN*0..1]->(s:SERVICE) "
        "RETURN s.name AS service LIMIT 50"
    ),
}

from neo4j import GraphDatabase

uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
username = os.environ.get("NEO4J_USERNAME", "neo4j")
password = os.environ.get("NEO4J_PASSWORD", "")

if template_name not in TEMPLATES:
    print(json.dumps({"template": template_name, "records": [], "params_used": {}, "error": "unknown template"}, ensure_ascii=True))
if not password:
    print(json.dumps({"template": template_name, "records": [], "params_used": params, "error": "NEO4J_PASSWORD not set"}, ensure_ascii=True))

records = []
error = None
driver = GraphDatabase.driver(uri, auth=(username, password))
try:
    with driver.session(default_access_mode="READ") as session:
        result = session.run(TEMPLATES[template_name], **params)
        for record in result:
            records.append({key: str(value) for key, value in record.items()})
except Exception as exc:  # noqa: BLE001
    error = str(exc)[:300]
finally:
    driver.close()

print(json.dumps({"template": template_name, "records": records, "params_used": params, "error": error}, ensure_ascii=True))

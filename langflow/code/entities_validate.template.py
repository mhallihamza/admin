# Graph population — validate extracted entities/relations against the allowed schema.
# Input : @@VAR:context@@ = raw model output text (JSON expected:
#         {"entities":[{"label":"PROCEDURE","name":"...","properties":{...}}, ...],
#          "relations":[{"type":"REQUIRES","source":"PROCEDURE:...","target":"DOCUMENT:...","properties":{...}}]})
# Output: printed JSON { entities, relations, rejected } — only schema-valid items survive.
# The Neo4j writer NEVER receives free-form Cypher — only this validated JSON.

import json
import ast
import re

RAW = r@@QUOTE@@
@@VAR:context@@
@@QUOTE@@

ALLOWED_ENTITY_LABELS = {
    "ADMINISTRATION", "SERVICE", "PROCEDURE", "DOCUMENT", "LAW",
    "ARTICLE", "CITY", "FORM", "REQUIREMENT",
}
ALLOWED_RELATION_TYPES = {
    "BELONGS_TO", "REQUIRES", "SUPERSEDES", "MANAGED_BY", "LOCATED_IN", "CITES", "PART_OF",
}
MAX_NAME_LENGTH = 200

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
rejected = []

def valid_name(name):
    return isinstance(name, str) and 0 < len(name) <= MAX_NAME_LENGTH

entities = []
seen_entities = set()
for entity in payload.get("entities", []) if isinstance(payload.get("entities"), list) else []:
    label = str(entity.get("label", "")).upper()
    name = entity.get("name")
    if label not in ALLOWED_ENTITY_LABELS:
        rejected.append({"kind": "entity", "reason": f"label {label} not allowed"})
        continue
    if not valid_name(name):
        rejected.append({"kind": "entity", "reason": "invalid name"})
        continue
    key = f"{label}:{name}"
    if key in seen_entities:
        continue
    seen_entities.add(key)
    entities.append({"label": label, "name": name})

valid_keys = {f"{e['label']}:{e['name']}" for e in entities}

relations = []
seen_relations = set()
for relation in payload.get("relations", []) if isinstance(payload.get("relations"), list) else []:
    rel_type = str(relation.get("type", "")).upper()
    source = relation.get("source")
    target = relation.get("target")
    if rel_type not in ALLOWED_RELATION_TYPES:
        rejected.append({"kind": "relation", "reason": f"type {rel_type} not allowed"})
        continue
    if source not in valid_keys or target not in valid_keys:
        rejected.append({"kind": "relation", "reason": "unknown endpoint entity"})
        continue
    key = f"{source}-[{rel_type}]->{target}"
    if key in seen_relations:
        continue
    seen_relations.add(key)
    relations.append({"type": rel_type, "source": source, "target": target})

print(json.dumps({"entities": entities, "relations": relations, "rejected": rejected}, ensure_ascii=True))

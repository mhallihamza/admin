# Graph population — write validated entities/relations to Neo4j.
# Input : @@VAR:context@@ = JSON from the schema-validation step { entities, relations }
# Output: printed JSON { written_entities, written_relations, errors }
#
# SECURITY: only the FIXED parameterized MERGE queries below are ever executed.
# No query is built from user text; validated values travel only as parameters.
# Requires the neo4j driver in the Langflow environment: pip install neo4j
# Environment variables: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

import json
import os

RAW = r@@QUOTE@@
@@VAR:context@@
@@QUOTE@@

payload = json.loads(RAW)

from neo4j import GraphDatabase

uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
username = os.environ.get("NEO4J_USERNAME", "neo4j")
password = os.environ.get("NEO4J_PASSWORD", "")
if not password:
    print(json.dumps({"written_entities": 0, "written_relations": 0, "errors": ["NEO4J_PASSWORD not set"]}, ensure_ascii=True))

# Fixed, parameterized queries — the ONLY writes this flow can perform.
# NOTE: Cypher cannot parameterize labels/rel-types; the whitelists below are
# re-checked here before the label/type is substituted into the fixed template.
ALLOWED_LABELS = {"ADMINISTRATION", "SERVICE", "PROCEDURE", "DOCUMENT", "LAW", "ARTICLE", "CITY", "FORM", "REQUIREMENT"}
ALLOWED_RELATION_TYPES = {"BELONGS_TO", "REQUIRES", "SUPERSEDES", "MANAGED_BY", "LOCATED_IN", "CITES", "PART_OF"}

def entity_query(label):
    safe_label = label if label in ALLOWED_LABELS else "REJECTED"
    return "MERGE (n:`" + safe_label + "` {name: $name}) ON CREATE SET n.created_at = datetime()"

def relation_query(rel_type):
    safe_type = rel_type if rel_type in ALLOWED_RELATION_TYPES else "UNKNOWN"
    return (
        "MATCH (a {name: $source}), (b {name: $target}) "
        "MERGE (a)-[r:`" + safe_type + "`]->(b) "
        "ON CREATE SET r.created_at = datetime()"
    )

written_entities = 0
written_relations = 0
errors = []

driver = GraphDatabase.driver(uri, auth=(username, password))
try:
    with driver.session(default_access_mode="WRITE") as session:
        for entity in payload.get("entities", []):
            if entity["label"] not in ALLOWED_LABELS:
                continue
            session.execute_write(lambda tx, e: tx.run(entity_query(e["label"]), name=e["name"]).consume(),
                                  dict(entity))
            written_entities += 1
        for relation in payload.get("relations", []):
            if relation["type"] not in ALLOWED_RELATION_TYPES:
                continue
            session.execute_write(
                lambda tx, r: tx.run(relation_query(r["type"]), source=r["source"], target=r["target"]).consume(),
                dict(relation),
            )
            written_relations += 1
finally:
    driver.close()

print(json.dumps({"written_entities": written_entities, "written_relations": written_relations, "errors": errors}, ensure_ascii=True))

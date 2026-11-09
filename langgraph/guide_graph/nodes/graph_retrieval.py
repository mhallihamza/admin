# =====================================================================
# Graph retrieval (flow 05) : templates Cypher FIXES en lecture seule.
# Aucune requête construite depuis le texte utilisateur : un template
# inconnu => erreur "unknown template", le Cypher brut n'est JAMAIS
# exécuté (session READ partout).
# =====================================================================
from __future__ import annotations

from ..tools.neo4j_store import Neo4jAdapter
from ..tracing import mark_start, record_timing

GRAPH_TEMPLATES = {
    "procedure_requirements":
        "MATCH (p:PROCEDURE {name: $procedure_name})-[:REQUIRES]->(d) RETURN d.name AS requirement LIMIT 50",
    "procedure_administration":
        "MATCH (p:PROCEDURE {name: $procedure_name})-[:BELONGS_TO]->(a) RETURN a.name AS administration LIMIT 10",
    "documents_of_law":
        "MATCH (l:LAW {name: $law_name})-[:PART_OF]->(d:DOCUMENT) RETURN d.name AS document LIMIT 50",
    "administration_services":
        "MATCH (a:ADMINISTRATION {name: $administration_name})-[:MANAGED_BY|LOCATED_IN*0..1]->(s:SERVICE) RETURN s.name AS service LIMIT 50",
}


def run_template_query(template: str, params: dict, adapter: Neo4jAdapter | None = None) -> dict:
    if template not in GRAPH_TEMPLATES:
        return {"template": template, "records": [], "params_used": {},
                "error": "unknown template"}
    cypher = GRAPH_TEMPLATES[template]
    if adapter is None:
        adapter = Neo4jAdapter.from_config("READ")
    outcome = adapter.run_template(cypher, params or {})
    return {"template": template, "records": outcome.get("records", []),
            "params_used": params or {}, "error": outcome.get("error")}


def node_graph_retrieve(state: dict) -> dict:
    started = mark_start()
    inject = state.get("_inject") or {}
    outcome = run_template_query(
        state.get("graph_template", ""), state.get("graph_params", {}) or {},
        adapter=inject.get("neo4j"),
    )
    return {
        "graph_records": outcome.get("records", []),
        "graph_error": outcome.get("error"),
        **record_timing(state, "graph_retrieve", started),
    }


def build_graph_retrieval_graph():
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("graph_retrieve", node_graph_retrieve)
    builder.add_edge(START, "graph_retrieve")
    builder.add_edge("graph_retrieve", END)
    return builder.compile()


def run_graph_retrieval(template: str, params: dict, neo4j=None) -> dict:
    result = build_graph_retrieval_graph().invoke({
        "graph_template": template or "", "graph_params": dict(params or {}),
        "_inject": {"neo4j": neo4j},
    })
    return {"template": template, "records": result.get("graph_records", []),
            "error": result.get("graph_error")}

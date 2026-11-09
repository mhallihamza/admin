# =====================================================================
# Population du graphe (flow 03) : extraction d'entités (Mistral,
# structured JSON) → validation du schéma autorisé → MERGE Neo4j avec
# templates FIXES uniquement. Double vérification : validateur + writer.
# =====================================================================
from __future__ import annotations

from .. import llm as llm_mod
from ..llm import make_llm
from ..prompts import EXTRACTION_PROMPT
from ..tools import neo4j_store
from ..tracing import mark_start, record_timing

EMPTY_EXTRACTION = {"entities": [], "relations": [], "rejected": []}


# ---------------------------------------------------------------------------
# Nœud — extraction (le seul appel modèle de ce flow)
# ---------------------------------------------------------------------------
def node_extract(state: dict) -> dict:
    started = mark_start()
    block, mode, usage = llm_mod.call_llm_json(
        _llm(state, temperature=0.1),
        EXTRACTION_PROMPT.format(chunk_text=str(state.get("raw_text", ""))[:8000]),
        fallback=dict(EMPTY_EXTRACTION),
    )
    entities = block.get("entities") if isinstance(block.get("entities"), list) else []
    relations = block.get("relations") if isinstance(block.get("relations"), list) else []
    usage_merge = llm_mod.merge_usage(state, usage)
    return {**record_timing(state, "extract", started),
            "extraction": {"entities": entities, "relations": relations, "rejected": [],
                            "mode": mode},
            "llm_mode": mode, **usage_merge}


def _llm(state: dict, temperature: float = 0.1):
    inject = state.get("_inject") or {}
    if inject.get("llm") is not None:
        return inject["llm"]
    model, _mode = make_llm(temperature=temperature)
    return model


# ---------------------------------------------------------------------------
# Validation du schéma autorisé (entities_validate.template.py)
# ---------------------------------------------------------------------------
def validate_extraction(entities: list[dict], relations: list[dict]) -> dict:
    """Whitelist stricte, dédoublonnage, noms <= 200, affine relations."""
    seen: set = set()
    valid_entities: list[dict] = []
    rejected: list[str] = []
    for ent in entities or []:
        label, name = str(ent.get("label", "")), str(ent.get("name", ""))
        key = f"{label}:{name}"
        if label not in neo4j_store.ALLOWED_LABELS:
            rejected.append(f"UNKNOWN_LABEL {label!r}")
            continue
        if not name.strip() or len(name) > neo4j_store.MAX_NAME_LENGTH:
            rejected.append(f"BAD_NAME {name[:50]!r}")
            continue
        if key in seen:
            continue
        seen.add(key)
        valid_entities.append({"label": label, "name": name})

    entity_keys = {f"{e['label']}:{e['name']}" for e in valid_entities}
    valid_relations: list[dict] = []
    seen_rel: set = set()
    for rel in relations or []:
        rel_type, source, target = (str(rel.get("type", "")), str(rel.get("source", "")),
                                    str(rel.get("target", "")))
        if rel_type not in neo4j_store.ALLOWED_RELATION_TYPES:
            rejected.append(f"UNKNOWN_TYPE {rel_type!r}")
            continue
        if source not in entity_keys or target not in entity_keys:
            rejected.append(f"ORPHAN_RELATION {source}->{target}")
            continue
        key = (rel_type, source, target)
        if key in seen_rel:
            continue
        seen_rel.add(key)
        valid_relations.append({"type": rel_type, "source": source, "target": target})

    return {"entities": valid_entities, "relations": valid_relations, "rejected": rejected}


def node_validate(state: dict) -> dict:
    started = mark_start()
    extraction = state.get("extraction") or {}
    result = validate_extraction(extraction.get("entities", []), extraction.get("relations", []))
    result["mode"] = extraction.get("mode", "none")
    return {**record_timing(state, "validate", started), "extraction": result}


# ---------------------------------------------------------------------------
# Écriture Neo4j (neo4j_write.template.py — MERGE uniquement, whitelist)
# ---------------------------------------------------------------------------
def node_write(state: dict) -> dict:
    started = mark_start()
    inject = state.get("_inject") or {}
    adapter = inject.get("neo4j")
    if adapter is None:
        adapter = neo4j_store.Neo4jAdapter.from_config("WRITE")
    summary = adapter.write_entities_and_relations(
        (state.get("extraction") or {}).get("entities", []),
        (state.get("extraction") or {}).get("relations", []),
    )
    if hasattr(adapter, "close"):
        adapter.close()
    return {**record_timing(state, "write", started), "write_summary": summary}


def build_population_graph():
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("extract", node_extract)
    builder.add_node("validate", node_validate)
    builder.add_node("write", node_write)
    builder.add_edge(START, "extract")
    builder.add_edge("extract", "validate")
    builder.add_edge("validate", "write")
    builder.add_edge("write", END)
    return builder.compile()


def run_population(chunk_text: str, neo4j=None, llm=None) -> dict:
    result = build_population_graph().invoke({
        "raw_text": chunk_text or "",
        "_inject": {"neo4j": neo4j, "llm": llm},
    })
    return {"extraction": result.get("extraction"), "write_summary": result.get("write_summary")}

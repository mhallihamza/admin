# =====================================================================
# Vector retrieval (flow 04) : embeddings → Astra `admin_guide_chunks`
# → filtre déterministe APPROVED + is_current uniquement.
# Aucun modèle génératif — juste l'embedding mistral-embed.
# =====================================================================
from __future__ import annotations

from .. import config
from ..tools.astra import InMemoryVectorSink, _identity_embedding
from ..tracing import mark_start, record_timing

# Nombre de candidats : le flow Langflow cherchait 12, filtrait après.
TOP_K = 12


def node_retrieve(state: dict) -> dict:
    started = mark_start()
    inject = state.get("_inject") or {}
    query = str(state.get("query", ""))[:2000]
    top_k = int(inject.get("top_k") or TOP_K)

    sink = inject.get("sink") or None
    if sink is None:
        if config.astra_ready():
            from ..tools.astra import AstraVectorSink

            sink = AstraVectorSink.from_settings()
        else:
            sink = InMemoryVectorSink()

    if inject.get("embeddings") is not None:
        vec = inject["embeddings"].embed_query(query)
    elif config.llm_ready():
        from ..tools.astra import default_embeddings

        vec = default_embeddings().embed_query(query)
    else:
        vec = _identity_embedding(query)   # fallback déterministe (tests)

    hits = sink.search(vec, top_k=top_k)
    kept, dropped = filter_chunks(hits)
    return {
        "chunks_meta": kept,
        "dropped": dropped,
        "criteria": {"approval_status": "APPROVED", "is_current": True},
        **record_timing(state, "retrieve", started),
    }


def filter_chunks(hits: list[dict]) -> tuple[list[dict], int]:
    """Le filtre de sécurité RAG : seuls les chunks APPROVED et courants
    rentrent dans le contexte. Déterministe, pas de modèle."""
    kept: list[dict] = []
    for hit in hits or []:
        meta = hit.get("metadata") or {}
        if meta.get("approval_status") != "APPROVED":
            continue
        if meta.get("is_current") is False:
            continue
        kept.append({"text": hit.get("text", ""), "metadata": meta})
    return kept, len(hits or []) - len(kept)


def build_retrieval_graph():
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("retrieve", node_retrieve)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", END)
    return builder.compile()


def run_retrieval(query: str, top_k: int = TOP_K, sink=None, embeddings=None) -> dict:
    result = build_retrieval_graph().invoke({
        "query": query or "",
        "_inject": {"sink": sink, "embeddings": embeddings, "top_k": top_k},
    })
    return {"results": result.get("chunks_meta", []), "dropped": result.get("dropped", 0),
            "criteria": result.get("criteria")}

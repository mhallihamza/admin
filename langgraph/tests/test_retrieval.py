# =====================================================================
# flow 04 — vector retrieval : le filtre APPROVED + is_current est le
# cœur de sécurité du RAG (Approuvé seulement, une version à la fois).
# =====================================================================
from __future__ import annotations

from guide_graph.nodes import retrieval
from guide_graph.tools.astra import InMemoryVectorSink


def _chunk(doc, article="1", status="APPROVED", current=True, text="t"):
    return {"text": text,
            "metadata": {"document_id": doc, "article_number": article,
                         "version": "1", "approval_status": status,
                         "is_current": current}}


def test_filter_keeps_only_approved_and_current():
    hits = [
        _chunk("DOC-0001", "1", "APPROVED", True),
        _chunk("DOC-0002", "1", "PENDING_REVIEW", True),
        _chunk("DOC-0003", "1", "APPROVED", False),   # version supercedée
        _chunk("DOC-0004", "1", "REJECTED", True),
    ]
    kept, dropped = retrieval.filter_chunks(hits)
    assert [k["metadata"]["document_id"] for k in kept] == ["DOC-0001"]
    assert dropped == 3


def test_retrieve_returns_only_filtered_results():
    sink = InMemoryVectorSink()
    sink.add_chunks([
        {"text": "approuvé", "metadata": _chunk("DOC-0001", status="APPROVED")["metadata"]},
        {"text": "en attente", "metadata": _chunk("DOC-0002", status="PENDING_REVIEW")["metadata"]},
    ])
    out = retrieval.run_retrieval("renouvellement carte", sink=sink)
    assert out["results"]
    assert all(r["metadata"]["approval_status"] == "APPROVED" for r in out["results"])
    assert out["dropped"] >= 1
    assert out["criteria"] == {"approval_status": "APPROVED", "is_current": True}

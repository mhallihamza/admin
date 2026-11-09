# =====================================================================
# flow 07 — validation déterministe des citations (sans modèle) :
# chaque citation doit exister, être APPROVED et courante.
# =====================================================================
from __future__ import annotations

from guide_graph.nodes import validation


def _chunk(doc, article, version, status="APPROVED", current=True):
    return {"metadata": {"document_id": doc, "article_number": article,
                         "version": version, "approval_status": status,
                         "is_current": current}}


def test_valid_citation():
    answer = "réponse...\nSources:\n- DOC-0001, article 12, version 1"
    citations = validation.extract_citations(answer)
    assert citations == [{"document_id": "DOC-0001", "article_number": "12", "version": "1"}]
    verdict = validation.validate_citations(citations, [_chunk("DOC-0001", "12", "1")])
    assert verdict == {"valid": True, "invalid_citations": [], "checked_count": 1}


def test_pending_review_document_invalid():
    citations = [{"document_id": "DOC-0002", "article_number": "3", "version": "1"}]
    chunks = [_chunk("DOC-0002", "3", "1", status="PENDING_REVIEW")]
    verdict = validation.validate_citations(citations, chunks)
    assert verdict["valid"] is False
    assert verdict["invalid_citations"] == citations


def test_superseded_version_invalid():
    citations = [{"document_id": "DOC-0001", "article_number": "5", "version": "1"}]
    chunks = [_chunk("DOC-0001", "5", "1", current=False)]
    assert validation.validate_citations(citations, chunks)["valid"] is False


def test_zero_citations_invalid():
    verdict = validation.validate_citations([], [_chunk("DOC-0001", "1", "1")])
    assert verdict["valid"] is False
    assert verdict["checked_count"] == 0


def test_extraction_without_sources_section():
    assert validation.extract_citations("aucune source ici") == []


def test_arabic_article_extraction():
    answer = "المصادر:\n- DOC-0003، المادة 7، نسخة 2"
    citations = validation.extract_citations(answer)
    assert citations[0]["document_id"] == "DOC-0003"
    assert citations[0]["article_number"] == "7"

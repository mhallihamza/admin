# =====================================================================
# Validation de la réponse (flow 07) — DÉTERMINISTE, aucun modèle.
# Chaque citation (document_id, article_number, version) doit pointer
# vers un chunk APPROVED et courant. Zéro citation => valid=False.
# Une réponse invalide est RETENUE (answer_final=None) — le backend
# bloque la réponse, en accord avec la build-sheet.
# =====================================================================
from __future__ import annotations

import re

from ..tracing import mark_start, record_timing


def extract_citations(answer: str, known_doc_ids: list[str] | None = None) -> list[dict]:
    """Extrait les lignes 'Sources:' de la réponse en citations
    structurées ; formats tolérés :
      - DOC-0001, article 12, version 1
      - DOC-0001 (article 12)
      - <document_id réel>, article 12, version 1  (ex. doc-demo-cnie-001)
    Les identifiants réels des chunks retrievés (known_doc_ids) sont
    reconnus en plus du format de référence DOC-<numéro>."""
    citations: list[dict] = []
    known = sorted({d for d in (known_doc_ids or []) if d}, key=len, reverse=True)
    for line in str(answer or "").splitlines():
        doc_id: str | None = None
        doc_match = re.search(r"\bDOC[-_ ]?(\d{3,})\b", line, re.I)
        if doc_match:
            doc_id = f"DOC-{doc_match.group(1)}"
        else:
            for candidate in known:
                if candidate and candidate.lower() in line.lower():
                    doc_id = candidate
                    break
        if doc_id is None:
            continue
        article = re.search(r"article\s*[^\d]*(\d+)", line, re.I) or re.search(r"المادة\s*(\d+)", line)
        version = re.search(r"version\s*[^\d]*(\d+)", line, re.I)
        citations.append({
            "document_id": doc_id,
            "article_number": article.group(1) if article else "0",
            "version": version.group(1) if version else "1",
        })
    return citations


def validate_citations(citations: list[dict], chunks: list[dict]) -> dict:
    """La RÈGLE : toute citation doit exister, être APPROVED et courante.
    valid = aucune citation invalide ET au moins une citation (zéro
    citation => valid false)."""
    approved_keys = {
        (str(c.get("metadata", {}).get("document_id", "")),
         # convention build-sheet : un chunk sans article cite "article 0"
         str(c.get("metadata", {}).get("article_number") or "0"),
         str(c.get("metadata", {}).get("version", "")))
        for c in chunks or []
        if c.get("metadata", {}).get("approval_status") == "APPROVED"
        and c.get("metadata", {}).get("is_current") is not False
    }
    invalid: list[dict] = []
    for citation in citations or []:
        key = (str(citation.get("document_id", "")),
               str(citation.get("article_number", "")),
               str(citation.get("version", "")))
        if key not in approved_keys:
            invalid.append(citation)
    return {
        "valid": len(invalid) == 0 and len(citations or []) > 0,
        "invalid_citations": invalid,
        "checked_count": len(citations or []),
    }


def node_validate(state: dict) -> dict:
    started = mark_start()
    chunks = state.get("chunks_meta") or state.get("chunks") or []
    citations = state.get("citations") or extract_citations(
        state.get("answer", ""),
        known_doc_ids=[(c.get("metadata") or {}).get("document_id", "") for c in chunks],
    )
    verdict = validate_citations(citations, chunks)
    answer_final = state.get("answer") if verdict["valid"] else None
    reason = "" if verdict["valid"] else (
        "Answer withheld: citations not backed by APPROVED/current documents."
        if verdict["checked_count"] else
        "Answer withheld: no citations found in the specialist answer."
    )
    return {**record_timing(state, "validate_answer", started),
            "citations": citations, "validation": verdict,
            "answer_final": answer_final,
            "gate_reason": reason if not verdict["valid"] else state.get("gate_reason", "")}

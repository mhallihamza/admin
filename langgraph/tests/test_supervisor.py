# =====================================================================
# flows 06 + 06a/b/c — supervisor & spécialistes : routage déterministe,
# payloads passerelle FIXES, réponse uniquement depuis les outils.
# =====================================================================
from __future__ import annotations

import json

from guide_graph.nodes import supervisor
from guide_graph.prompts import SPECIALIST_MARKERS


def _session(question, **over):
    session = {
        "question": question,
        "language": "fr",
        "user_token": "user-token-1",
        "gateway_base_url": "http://gateway.test",
    }
    session.update(over)
    return session


def test_intent_fallback_rules_match_sheet_tests():
    cases = [
        ("Quels documents pour renouveler la CIN ?" and
         "Comment renouveler ma carte d'identité ?", "PROCEDURE"),
        ("ما المادة القانونية المنظمة للبطاقة ؟", "LEGAL_RESEARCH"),
        ("حالة الوثيقة DOC-0001 ؟", "DOCUMENT_ADMIN"),
        ("Bonjour", "PROCEDURE"),           # fallback : jamais de réponse inventée
    ]
    for question, expected in cases:
        specialist, reason = supervisor.classify_intent_fallback(question)
        assert specialist == expected, f"{question!r} -> {specialist} ({reason})"


def test_procedure_specialist_uses_fixed_vector_payload(gateway_backend, fake_llm_factory):
    llm = fake_llm_factory("une réponse de spécialiste")
    outcome = supervisor.run_supervisor(_session("Comment renouveler ma carte ?"),
                                        http=gateway_backend, llm=llm)
    # 1) un appel token avec les corps exacts du contrat
    assert gateway_backend.calls["token_calls"] == [
        {"agent": "PROCEDURE_AGENT", "tool": "VECTOR_RETRIEVAL",
         "operation": "execute", "data_scope": "OWN"}]
    # 2) un appel outil avec le payload DÉTERMINISTE (jamais composé par le modèle)
    call = gateway_backend.calls["tool_calls"][0]
    assert call["path"] == "/api/tools/vector-retrieval"
    assert call["agent_token"] == "agent-token-1"
    assert call["payload"] == {"query": "Comment renouveler ma carte ?",
                               "language": "fr", "top_k": 6}


def test_legal_specialist_calls_vector_and_graph(gateway_backend, fake_llm_factory):
    llm = fake_llm_factory("réponse sans marqueur")
    outcome = supervisor.run_supervisor(_session("ما المادة القانونية المنظمة للبطاقة ؟",
                                                 language="ar"),
                                        http=gateway_backend, llm=llm)
    assert outcome["specialist"] == "LEGAL_RESEARCH"
    paths = [c["path"] for c in gateway_backend.calls["tool_calls"]]
    assert paths == ["/api/tools/vector-retrieval", "/api/tools/graph-retrieval"]
    graph_call = gateway_backend.calls["tool_calls"][1]
    assert graph_call["payload"]["template"] == "procedure_requirements"  # défaut fixe


def test_document_admin_specialist_fixed_payload(gateway_backend, fake_llm_factory):
    llm = fake_llm_factory("Document DOC-0001 present.")
    outcome = supervisor.run_supervisor(
        _session("حالة الوثيقة DOC-0001 ؟", document_id="DOC-0001"),
        http=gateway_backend, llm=llm)
    assert outcome["specialist"] == "DOCUMENT_ADMIN"
    call = gateway_backend.calls["tool_calls"][0]
    assert call["path"] == "/api/tools/document-index"
    assert call["payload"] == {"document_id": "DOC-0001"}


def test_denied_agent_tool_combo_gets_403(gateway_backend):
    """SUPERVISOR×DOCUMENT_INDEX hors des tables de permissions ->
    403 AGENT_TOKEN_DENIED au token, audité côté backend."""
    from guide_graph.tools import gateway_client

    outcome = gateway_client.call_gateway_tool(
        {"user_token": "user-token-1", "gateway_base_url": "http://gateway.test"},
        "SUPERVISOR", "DOCUMENT_INDEX", {"document_id": "DOC-0001"},
        http=gateway_backend)
    assert outcome["status"] == "denied"
    assert outcome["http_status"] == 403
    # aucun appel d'outil n'a été émis
    assert all(c["path"] != "/api/tools/document-index" for c in gateway_backend.calls["tool_calls"])


def test_heuristic_answer_only_official_content(gateway_backend):
    outcome = supervisor.run_supervisor(_session("Comment renouveler ma carte ?"),
                                        http=gateway_backend, llm=None)
    assert outcome["answer"].startswith("[PROCEDURE_AGENT]")
    assert "Renouvellement CIN" in outcome["answer"]          # contenu d'outil
    assert "aucune réponse n'est inventée" in outcome["answer"]


def test_marker_always_first_line(fake_llm_factory, gateway_backend):
    # le LLM factice renvoie une réponse SANS marqueur : il est préfixé
    llm = fake_llm_factory("juste du texte")
    outcome = supervisor.run_supervisor(_session("Comment faire ?"),
                                        http=gateway_backend, llm=llm)
    assert outcome["answer"].startswith("[PROCEDURE_AGENT]")

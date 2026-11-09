# =====================================================================
# flows 08 + 09 — handoff (via passerelle, HUMAN_HANDOFF) et journal
# d'exécution (POST /api/logs/execution, statut contrôlé).
# =====================================================================
from __future__ import annotations

from guide_graph.nodes import execution_log, handoff


def test_handoff_uses_agent_token_and_fixed_payload(gateway_backend):
    result = handoff.run_handoff_flow({
        "user_token": "user-token-1",
        "gateway_base_url": "http://gateway.test",
        "conversation_id": "conv-9",
        "question_summary": "Cas bloqué à réviser",
    }, http=gateway_backend)
    assert result["status"] == "handed_off"
    assert result["http_status"] == 200
    token_calls = gateway_backend.calls["token_calls"]
    assert token_calls[0]["agent"] == "SUPERVISOR"
    assert token_calls[0]["tool"] == "HUMAN_HANDOFF"
    call = gateway_backend.calls["tool_calls"][0]
    assert call["path"] == "/api/tools/human-handoff"
    assert call["payload"] == {"conversation_id": "conv-9",
                               "reason": "Cas bloqué à réviser"}


def test_handoff_denied_when_token_for_other_tool(gateway_backend):
    """agent_token émis pour un autre outil -> 403 refusé + audité côté
    backend ; le node rapporte 'denied' sans créer de cas."""
    session = {
        "user_token": "user-token-1",
        "gateway_base_url": "http://gateway.test",
        "conversation_id": "conv-1",
        "agent_token": "wrong-tool-token",   # pré-émis pour un autre outil
    }
    result = handoff.run_handoff_flow(session, http=gateway_backend)
    assert result["status"] == "denied"
    assert result["http_status"] == 403


def test_execution_log_success(gateway_backend):
    outcome = execution_log.log_execution(
        {"user_token": "user-token-1", "gateway_base_url": "http://gateway.test"},
        flow="guide-graph/chat-pipeline", status="SUCCESS",
        duration_ms=240, correlation_id="run-001", http=gateway_backend)
    assert outcome["status"] == "logged"
    sent = gateway_backend.calls["tool_calls"][0]
    assert sent["path"] == "/api/logs/execution"
    assert sent["agent_token"] is None           # PAS de token agent (comme le flow Langflow)
    assert sent["payload"]["status"] == "SUCCESS"


def test_execution_log_rejects_invalid_status(gateway_backend):
    outcome = execution_log.log_execution(
        {"user_token": "user-token-1", "gateway_base_url": "http://gateway.test"},
        flow="flow-8", status="MAYBE", duration_ms=1, http=gateway_backend)
    assert outcome["status"] == "failed"
    assert "invalid status" in str(outcome["body"])
    assert gateway_backend.calls["tool_calls"] == []

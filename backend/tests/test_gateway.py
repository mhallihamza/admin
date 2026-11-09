"""Tool gateway: agents may only call tools they are allowed to use, with a
short-lived backend-issued agent token. Every denial is audited."""

from __future__ import annotations

from tests.conftest import CITIZEN_ROLES, make_agent_token

USER_ID = "u-citizen"


def _auth_citizen(auth_factory):
    auth_factory(CITIZEN_ROLES, uid=USER_ID, email="citizen@test.ma")


def test_agent_token_denied_when_agent_not_allowed(
    client, auth_factory, permission_matrix, audit_capture
):
    _auth_citizen(auth_factory)
    permission_matrix["tool"][("CITIZEN", "DOCUMENT_INDEX", "execute", "OWN")] = True
    # SUPERVISOR is NOT allowed to use DOCUMENT_INDEX.
    permission_matrix["agent"][("SUPERVISOR", "VECTOR_RETRIEVAL", "execute")] = True

    response = client.post(
        "/api/gateway/token",
        json={"agent": "SUPERVISOR", "tool": "DOCUMENT_INDEX", "operation": "execute", "data_scope": "OWN"},
    )
    assert response.status_code == 403
    assert any(
        e["kwargs"].get("action") == "AGENT_TOKEN_DENIED" for e in audit_capture["events"]
    )


def test_agent_token_denied_when_role_not_allowed(
    client, auth_factory, permission_matrix, audit_capture
):
    _auth_citizen(auth_factory)
    # Role is not allowed for the tool even though the agent is.
    permission_matrix["agent"][("SUPERVISOR", "DOCUMENT_INDEX", "execute")] = True

    response = client.post(
        "/api/gateway/token",
        json={"agent": "SUPERVISOR", "tool": "DOCUMENT_INDEX", "operation": "execute", "data_scope": "OWN"},
    )
    assert response.status_code == 403


def test_agent_token_issued_when_allowed(client, auth_factory, permission_matrix):
    _auth_citizen(auth_factory)
    permission_matrix["tool"][("CITIZEN", "VECTOR_RETRIEVAL", "execute", "OWN")] = True
    permission_matrix["agent"][("PROCEDURE_AGENT", "VECTOR_RETRIEVAL", "execute")] = True

    response = client.post(
        "/api/gateway/token",
        json={"agent": "PROCEDURE_AGENT", "tool": "VECTOR_RETRIEVAL", "operation": "execute", "data_scope": "OWN"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_token"]
    assert body["expires_in"] <= 60


def test_tool_call_denied_for_agent_without_permission(
    client, auth_factory, permission_matrix, audit_capture
):
    """The required test: a tool call by an agent that is not allowed to use it."""
    _auth_citizen(auth_factory)
    # Role allowed, agent NOT allowed for DOCUMENT_INDEX.
    permission_matrix["tool"][("CITIZEN", "DOCUMENT_INDEX", "execute", "OWN")] = True

    token = make_agent_token(USER_ID, "PROCEDURE_AGENT", "DOCUMENT_INDEX", CITIZEN_ROLES)
    response = client.post(
        "/api/tools/document-index",
        json={"document_id": "D-301"},
        headers={"X-Agent-Token": token},
    )
    assert response.status_code == 403
    assert any(e["kwargs"].get("action") == "TOOL_DENIED" for e in audit_capture["events"])


def test_tool_call_rejects_token_for_other_tool(client, auth_factory, permission_matrix):
    _auth_citizen(auth_factory)
    permission_matrix["tool"][("CITIZEN", "VECTOR_RETRIEVAL", "execute", "OWN")] = True
    permission_matrix["agent"][("PROCEDURE_AGENT", "VECTOR_RETRIEVAL", "execute")] = True

    token = make_agent_token(USER_ID, "PROCEDURE_AGENT", "VECTOR_RETRIEVAL", CITIZEN_ROLES)
    response = client.post(
        "/api/tools/graph-retrieval",
        json={"template": "procedure_by_admin", "params": {}},
        headers={"X-Agent-Token": token},
    )
    assert response.status_code == 403


def test_tool_call_succeeds_with_allowed_agent(client, auth_factory, permission_matrix, audit_capture):
    _auth_citizen(auth_factory)
    permission_matrix["tool"][("CITIZEN", "VECTOR_RETRIEVAL", "execute", "OWN")] = True
    permission_matrix["agent"][("PROCEDURE_AGENT", "VECTOR_RETRIEVAL", "execute")] = True

    token = make_agent_token(USER_ID, "PROCEDURE_AGENT", "VECTOR_RETRIEVAL", CITIZEN_ROLES)
    response = client.post(
        "/api/tools/vector-retrieval",
        json={"query": "comment renouveler ma carte", "language": "fr", "top_k": 5},
        headers={"X-Agent-Token": token},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert audit_capture["events"] == []  # nothing denied, nothing audited as denial


def test_expired_agent_token_rejected(client, auth_factory, permission_matrix):
    _auth_citizen(auth_factory)
    token = make_agent_token(
        USER_ID, "PROCEDURE_AGENT", "VECTOR_RETRIEVAL", CITIZEN_ROLES, exp_offset=-10
    )
    response = client.post(
        "/api/tools/vector-retrieval",
        json={"query": "test"},
        headers={"X-Agent-Token": token},
    )
    assert response.status_code == 401


def test_missing_agent_token_rejected(client, auth_factory):
    _auth_citizen(auth_factory)
    response = client.post("/api/tools/vector-retrieval", json={"query": "test"})
    assert response.status_code == 422  # header required

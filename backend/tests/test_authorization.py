"""Unauthorized role access: endpoints must fail closed (401/403)."""

from __future__ import annotations

from tests.conftest import APPROVER_ROLES, CITIZEN_ROLES, VISITOR_ROLES


def test_me_requires_token(client):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_upload_forbidden_for_citizen(client, auth_factory, db_stub, audit_capture):
    auth_factory(CITIZEN_ROLES)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    # Role checks fail closed in the authorization dependency, before any
    # processing: no file is read, no document row is created.
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role."


def test_upload_forbidden_for_employee(client, auth_factory, db_stub):
    auth_factory(["EMPLOYEE"])
    response = client.post(
        "/api/documents/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 403


def test_upload_allowed_for_content_approver(client, auth_factory, db_stub, audit_capture):
    auth_factory(APPROVER_ROLES)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("note.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "UPLOADED"
    assert body["validation"]["extension"] == "txt"


def test_disabled_account_rejected_even_with_role(client, auth_factory):
    auth_factory(APPROVER_ROLES, disabled=True)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("note.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 403


def test_security_gate_blocks_visitor_chat(client, auth_factory, audit_capture):
    auth_factory(VISITOR_ROLES)
    response = client.post("/api/security/gate", json={"text": "hi", "request_type": "chat"})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "BLOCK"
    assert any(v["rule"] == "ROLE_VS_REQUEST" for v in body["layer1_violations"])
    assert len(audit_capture["incidents"]) == 1


def test_security_gate_allows_citizen_chat(client, auth_factory, audit_capture):
    auth_factory(CITIZEN_ROLES)
    response = client.post(
        "/api/security/gate", json={"text": "Question about my procedure", "request_type": "chat"}
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "ALLOW"
    assert len(audit_capture["incidents"]) == 0


def test_security_gate_blocks_other_users_data(client, auth_factory, audit_capture):
    auth_factory(CITIZEN_ROLES, uid="u-1")
    response = client.post(
        "/api/security/gate",
        json={"text": "hi", "request_type": "chat", "source_user_id": "u-999"},
    )
    assert response.json()["decision"] == "BLOCK"

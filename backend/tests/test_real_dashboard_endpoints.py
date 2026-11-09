"""Offline contract checks for the real dashboard endpoints (no live DB)."""

from __future__ import annotations

from app import db
from tests.conftest import CITIZEN_ROLES, VISITOR_ROLES

ADMIN_ROLES = ["SYSTEM_ADMIN"]
AUDITOR_ROLES = ["SECURITY_AUDITOR"]
REVIEW_ROLES = ["EMPLOYEE"]
APPROVER_ROLES = ["CONTENT_APPROVER"]


def test_conversations_list_returns_message_count(client, auth_factory, monkeypatch):
    auth_factory(CITIZEN_ROLES)

    class FakeTimestamp:
        def isoformat(self):
            return "2026-11-08T10:00:00"

    monkeypatch.setattr(
        db,
        "fetch_all",
        lambda query, params=(): [
            {"id": "conv-1", "title": "Renouvellement CIN",
             "updated_at": FakeTimestamp(), "message_count": 4},
        ],
    )
    response = client.get("/api/conversations")
    assert response.status_code == 200
    assert response.json()["conversations"] == [{
        "id": "conv-1",
        "title": "Renouvellement CIN",
        "updated_at": "2026-11-08T10:00:00",
        "message_count": 4,
    }]


def test_document_status_rejects_unknown_value(client, auth_factory):
    auth_factory(APPROVER_ROLES)
    response = client.patch("/api/documents/not-a-doc/status", json={"status": "PUBLISHED"})
    assert response.status_code == 422


def test_admin_users_list_is_admin_only(client, auth_factory):
    auth_factory(CITIZEN_ROLES)
    response = client.get("/api/admin/users")
    assert response.status_code == 403


def test_admin_audit_events_and_workflows_read(client, auth_factory, monkeypatch):
    auth_factory(ADMIN_ROLES)
    monkeypatch.setattr(db, "fetch_all", lambda query, params=(): [])
    monkeypatch.setattr(db, "fetch_one", lambda query, params=(): {
        "users": 7, "requests_today": 2, "blocked_requests": 1, "workflow_errors": 0})
    assert client.get("/api/admin/audit-events").json()["events"] == []
    assert client.get("/api/admin/workflows").json()["workflows"] == []
    overview = client.get("/api/admin/overview").json()
    assert overview["users"] == 7
    assert overview["requestsToday"] == 2
    assert overview["blockedRequests"] == 1


def test_permissions_matrix_shape(client, auth_factory, monkeypatch):
    auth_factory(ADMIN_ROLES)
    monkeypatch.setattr(db, "fetch_all", lambda query, params=(): [
        {"agent": "SUPERVISOR", "tool": "HUMAN_HANDOFF", "allowed": True},
    ] + [
        {"agent": "SUPERVISOR", "tool": tool, "allowed": False}
        for tool in ("VECTOR_RETRIEVAL", "GRAPH_RETRIEVAL", "DOCUMENT_INDEX", "SECURITY_GATE")
    ] + [
        {"agent": agent, "tool": tool, "allowed": False}
        for agent in ("PROCEDURE_AGENT", "LEGAL_RESEARCH_AGENT", "DOCUMENT_ADMIN_AGENT", "DETECTION_AGENT")
        for tool in ("VECTOR_RETRIEVAL", "GRAPH_RETRIEVAL", "DOCUMENT_INDEX", "SECURITY_GATE", "HUMAN_HANDOFF")
    ])
    body = client.get("/api/admin/permissions").json()
    assert body["permissions"]
    assert len(body["permissions"]) == 25
    assert any(p["agent"] == "SUPERVISOR" and p["tool"] == "HUMAN_HANDOFF" and p["allowed"]
               for p in body["permissions"])


def test_review_case_requires_note_for_correct_or_reject(client, auth_factory):
    auth_factory(REVIEW_ROLES)
    response = client.patch("/api/review-cases/not-a-case", json={"status": "REJECTED"})
    assert response.status_code == 422


def test_incident_reveal_requires_reason(client, auth_factory):
    auth_factory(AUDITOR_ROLES)
    response = client.post("/api/security/incidents/not-a-case/reveal", json={"reason": "x"})
    assert response.status_code == 422


def test_citizen_reminders_list_is_citizen_only(client, auth_factory, monkeypatch):
    auth_factory(ADMIN_ROLES)
    monkeypatch.setattr(db, "fetch_all", lambda query, params=(): [])
    assert client.get("/api/reminders").status_code == 200

    auth_factory(VISITOR_ROLES)
    assert client.get("/api/reminders").status_code == 403


def test_saved_procedure_detail_shape(client, auth_factory, monkeypatch):
    auth_factory(CITIZEN_ROLES)
    monkeypatch.setattr(db, "fetch_one", lambda query, params=(): {
        "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "title": "[PROCEDURE_AGENT] Étapes…",
        "procedure_snapshot": {"answer": "[PROCEDURE_AGENT]\nÉtapes …"},
        "created_at": "2026-11-09T00:00:00",
    })
    path = "/api/procedures/saved/7c9e6679-7425-40de-944b-e07fc1f90ae7"
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["saved"]["title"] == "Étapes…"

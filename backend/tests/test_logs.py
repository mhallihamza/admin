"""Workflow execution logging endpoint (used by Langflow flow 09)."""

from __future__ import annotations

from tests.conftest import CITIZEN_ROLES


def test_execution_log_written_to_audit(client, auth_factory, audit_capture):
    auth_factory(CITIZEN_ROLES, uid="u-flow", email="flow@test.ma")
    response = client.post(
        "/api/logs/execution",
        json={"flow": "01 - Central Security Gate", "status": "SUCCESS", "duration_ms": 240, "correlation_id": "run-001"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "logged"}
    assert any(e["kwargs"].get("action") == "WORKFLOW_EXECUTION" for e in audit_capture["events"])


def test_execution_log_rejects_bad_status(client, auth_factory, audit_capture):
    auth_factory(CITIZEN_ROLES, uid="u-flow", email="flow@test.ma")
    response = client.post(
        "/api/logs/execution",
        json={"flow": "flow-x", "status": "MAYBE", "duration_ms": 1},
    )
    assert response.status_code == 422
    assert audit_capture["events"] == []

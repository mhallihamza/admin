"""Offline test setup: no Supabase, no Postgres. Authentication is replaced
by dependency overrides; permission and audit lookups are patched at module
level so the gateway logic under test is the real code."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Environment BEFORE any app import (config caches settings).
os.environ.setdefault("AGENT_TOKEN_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("RATE_LIMIT_CHAT_PER_MIN", "3")
os.environ.setdefault("RATE_LIMIT_UPLOAD_PER_MIN", "10")
os.environ.setdefault("RATE_LIMIT_DEFAULT_PER_MIN", "120")
os.environ.setdefault("UPLOAD_MAX_SIZE_MB", "20")
os.environ.setdefault("UPLOAD_MAX_PAGES", "300")
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_DB_URL", "")
# Hard-set (not setdefault): this suite must stay offline even when the
# developer's root .env.local points LANGGRAPH_* at the live workflow
# service — otherwise Layer 2 is "configured", unreachable, and the gate
# fail-closes to REVIEW instead of the expected offline ALLOW.
os.environ["LANGGRAPH_SECURITY_GATE_URL"] = ""
os.environ["LANGGRAPH_BASE_URL"] = ""
os.environ["LANGGRAPH_FLOW_TOKEN"] = ""

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import audit, db, permissions  # noqa: E402
from app.auth import AuthUser, get_current_user  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rate_limit import rate_limiter  # noqa: E402

TEST_SECRET = "test-secret-key-for-pytest-only"

CITIZEN_ROLES = ["CITIZEN"]
APPROVER_ROLES = ["CONTENT_APPROVER"]
VISITOR_ROLES = ["VISITOR"]


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_factory(client):
    def _authenticate(roles: list[str], uid: str = "u-1", email: str = "user@test.ma", disabled: bool = False):
        user = AuthUser(id=uid, email=email, roles=list(roles), disabled=disabled)
        client.app.dependency_overrides[get_current_user] = lambda: user
        return user

    return _authenticate


@pytest.fixture
def permission_matrix(monkeypatch):
    """In-memory permission tables used by the real gateway/gate code."""
    state = {"tool": {}, "agent": {}}

    def tool_allowed(role: str, tool: str, operation: str, data_scope: str) -> bool:
        return state["tool"].get((role, tool, operation, data_scope), False)

    def agent_allowed(agent: str, tool: str, operation: str) -> bool:
        return state["agent"].get((agent, tool, operation), False)

    monkeypatch.setattr(permissions, "tool_permission_allowed", tool_allowed)
    monkeypatch.setattr(permissions, "agent_permission_allowed", agent_allowed)
    return state


@pytest.fixture
def audit_capture(monkeypatch):
    """Capture audit events and incidents emitted by the routers."""
    events: list[dict] = []
    incidents: list[dict] = []

    def capture_event(*args, **kwargs):
        events.append({"args": args, "kwargs": kwargs})

    def capture_incident(*args, **kwargs):
        incidents.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(audit, "log_event", capture_event)
    monkeypatch.setattr(audit, "log_incident", capture_incident)

    import app.routers.chat as chat_router
    import app.routers.documents as documents_router
    import app.routers.logs as logs_router
    import app.routers.security as security_router

    monkeypatch.setattr(chat_router, "log_event", capture_event)
    monkeypatch.setattr(chat_router, "log_incident", capture_incident)
    monkeypatch.setattr(documents_router, "log_event", capture_event)
    monkeypatch.setattr(logs_router, "log_event", capture_event)
    monkeypatch.setattr(security_router, "log_event", capture_event)
    monkeypatch.setattr(security_router, "log_incident", capture_incident)

    return {"events": events, "incidents": incidents}


@pytest.fixture
def db_stub(monkeypatch):
    """Stub the DB writes/reads used by the routers (documents upload)."""
    monkeypatch.setattr(db, "fetch_one", lambda query, params=(): {"id": "doc-1"})
    monkeypatch.setattr(db, "fetch_all", lambda query, params=(): [])
    monkeypatch.setattr(db, "execute", lambda query, params=(): None)


def make_agent_token(
    uid: str,
    agent: str,
    tool: str,
    roles: list[str],
    operation: str = "execute",
    data_scope: str = "OWN",
    exp_offset: int = 60,
) -> str:
    import time

    now = int(time.time())
    return jwt.encode(
        {
            "sub": uid,
            "agent": agent,
            "tool": tool,
            "operation": operation,
            "data_scope": data_scope,
            "roles": roles,
            "iat": now,
            "exp": now + exp_offset,
            "jti": "test-jti",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

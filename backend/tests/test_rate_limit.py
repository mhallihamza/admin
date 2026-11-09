"""Rate limiting: the chat endpoint allows RATE_LIMIT_CHAT_PER_MIN requests
per window (3 in tests) and then returns 429 with Retry-After."""

from __future__ import annotations

from tests.conftest import CITIZEN_ROLES


def test_chat_rate_limited(client, auth_factory, audit_capture):
    auth_factory(CITIZEN_ROLES, uid="u-rate", email="rate@test.ma")

    statuses = []
    for _ in range(5):
        response = client.post(
            "/api/chat/message",
            json={"text": "question about my procedure", "locale": "fr"},
        )
        statuses.append(response.status_code)

    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429
    assert statuses[4] == 429
    assert "Retry-After" in response.headers


def test_rate_limit_is_per_user(client, auth_factory, audit_capture):
    # Two different users each get their own window.
    auth_factory(CITIZEN_ROLES, uid="u-a", email="a@test.ma")
    first = client.post("/api/chat/message", json={"text": "hello"})
    assert first.status_code == 200

    auth_factory(CITIZEN_ROLES, uid="u-b", email="b@test.ma")
    second = client.post("/api/chat/message", json={"text": "hello"})
    assert second.status_code == 200

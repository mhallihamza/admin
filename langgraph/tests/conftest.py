# =====================================================================
# Garde-fou de la suite HORS-LIGNE : aucun test ne contacte un service
# réel (comme chez soukna). Toutes les clés externes sont vidées :
# mode heuristique partout ; le détecteur est faux (comportement
# scripté), la passerelle est simulée via httpx.MockTransport, les
# stores sont en mémoire.
# =====================================================================
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

# guide_graph importable depuis le dossier langgraph/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from guide_graph import config  # noqa: E402


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    """Aucune clé externe : mode heuristique partout, aucun service réel."""
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "")
    monkeypatch.setattr(config, "ASTRA_DB_APPLICATION_TOKEN", "")
    monkeypatch.setattr(config, "ASTRA_DB_API_ENDPOINT", "")
    monkeypatch.setattr(config, "NEO4J_PASSWORD", "")
    monkeypatch.setattr(config, "SUPABASE_URL", "")
    monkeypatch.setattr(config, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setattr(config, "BACKEND_GATEWAY_URL", "http://gateway.test")
    yield


@pytest.fixture
def detector_factory():
    """Fabricant de faux détecteurs Layer 2 (comportement scripté)."""
    def _make(*responses):
        queue = list(responses)
        def _detect(text: str):
            item = queue.pop(0) if queue else {"risk_level": "LOW", "attack_type": None,
                                               "confidence": 0.0, "reason": "clean"}
            if isinstance(item, Exception):
                raise item
            if isinstance(item, str):
                return json.loads(item)  # JSON malformé levé par l'appelant
            return item
        return _detect
    return _make


@pytest.fixture
def fail_detector():
    """Détecteur qui échoue (transport indisponible) — fail-closed."""
    def _detect(text: str):
        raise ConnectionError("detector transport down")
    return _detect


@pytest.fixture
def fake_llm_factory():
    """Faux LLM LangChain-style : renvoie une réponse scriptée."""
    class _Fake:
        def __init__(self, content: str):
            self.content = content

        def invoke(self, prompt):
            return _Fake(self.content)  # la réponse au prompt

        def bind(self, *args, **kwargs):
            return self

    def _make(content: str):
        return _Fake(content)
    return _make


@pytest.fixture
def gateway_backend():
    """Passerelle backend simulée : /api/gateway/token + /api/tools/*.
    Les payloads attendus sont enregistrés pour assertions."""
    calls: dict = {"tool_calls": [], "token_calls": []}

    def _handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content.decode() or "{}")
        if path == "/api/gateway/token":
            calls["token_calls"].append(body)
            agent, tool = body.get("agent"), body.get("tool")
            # matrice de permissions backend équivalent aux tables tool_permissions/agent_permissions :
            # PROCEDURE_AGENT×VECTOR_RETRIEVAL, LEGAL_RESEARCH_AGENT×(VECTOR, GRAPH),
            # DOCUMENT_ADMIN_AGENT×DOCUMENT_INDEX, SUPERVISOR×HUMAN_HANDOFF.
            allowed = {
                ("PROCEDURE_AGENT", "VECTOR_RETRIEVAL"),
                ("LEGAL_RESEARCH_AGENT", "VECTOR_RETRIEVAL"),
                ("LEGAL_RESEARCH_AGENT", "GRAPH_RETRIEVAL"),
                ("DOCUMENT_ADMIN_AGENT", "DOCUMENT_INDEX"),
                ("SUPERVISOR", "HUMAN_HANDOFF"),
            }
            if (agent, tool) not in allowed:
                return httpx.Response(403, json={"detail": "AGENT_TOKEN_DENIED"})
            return httpx.Response(200, json={"agent_token": "agent-token-1", "expires_in": 60})
        if path.startswith("/api/tools/"):
            calls["tool_calls"].append({"path": path, "agent_token": request.headers.get("x-agent-token"),
                                        "payload": body})
            if path == "/api/tools/vector-retrieval":
                return httpx.Response(200, json={
                    "status": "accepted", "results": [{
                        "text": "Renouvellement CIN : déposer le formulaire.",
                        "metadata": {"document_id": "DOC-0001", "article_number": "1",
                                     "version": "1", "approval_status": "APPROVED",
                                     "is_current": True},
                    }]})
            if path == "/api/tools/graph-retrieval":
                return httpx.Response(200, json={"status": "accepted", "records": [
                    {"administration": "Ministère de l'Intérieur"}]})
            if path == "/api/tools/document-index":
                return httpx.Response(200, json={
                    "status": "accepted", "results": [{
                        "text": "Document DOC-0001 : Rapport annuel 2026.",
                        "metadata": {"document_id": "DOC-0001", "article_number": "0",
                                     "version": "1", "approval_status": "APPROVED",
                                     "is_current": True},
                    }]})
            if path == "/api/tools/human-handoff":
                if request.headers.get("x-agent-token") != "agent-token-1":
                    return httpx.Response(403, json={"detail": "TOOL_DENIED"})
                return httpx.Response(200, json={"status": "created", "case_id": "case-7",
                                                 "status_case": "OPEN"})
            return httpx.Response(404, json={"detail": "no route"})
        if path == "/api/logs/execution":
            calls["tool_calls"].append({"path": path, "agent_token": None, "payload": body})
            return httpx.Response(200, json={"logged": True})
        return httpx.Response(404, json={"detail": "no route"})

    transport = httpx.MockTransport(_handler)
    client = httpx.Client(transport=transport)
    client.calls = calls
    return client

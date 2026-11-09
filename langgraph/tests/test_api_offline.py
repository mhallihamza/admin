# =====================================================================
# API offline (TestClient) : /health, auth X-Flow-Token, endpoints
# /run/* — aucune dépendance externe.
# =====================================================================
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client():
    return TestClient(api.app)


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "service": "guide-workflow"}


def test_flow_token_auth_required_when_configured(client, monkeypatch):
    from guide_graph import config

    monkeypatch.setattr(config, "FLOW_TOKEN", "s3cret")
    assert client.post("/run/security-gate", json={"payload": {}}).status_code == 401
    ok = client.post("/run/security-gate", json={"payload": {}},
                     headers={"X-Flow-Token": "s3cret"})
    assert ok.status_code == 200


def test_security_gate_endpoint_block(client):
    response = client.post("/run/security-gate", json={
        "payload": {"text": "x", "user_id": "u-1", "roles": ["VISITOR"],
                    "request_type": "chat", "disabled": False, "filename": None,
                    "source_user_id": None, "agent": None, "tool": None,
                    "agent_tool_allowed": None}})
    body = response.json()
    assert body["gate_decision"] == "BLOCK"
    assert body["layer1_violations"][0]["rule"] == "ROLE_VS_REQUEST"
    assert body["layer2"]["connected"] is False       # pas de clé : skip explicite


def test_security_gate_detector_http_contract(client, monkeypatch):
    """le backend appelle /run/detect comme il appelait le flow Langflow :
    même payload {text, request_type, user_id, filename}, même réponse
    {risk_level, attack_type, confidence, reason}."""
    payload_sent = {}

    def fake_detector(text):
        payload_sent["text"] = text
        return {"risk_level": "HIGH", "attack_type": "PROMPT_INJECTION",
                "confidence": 0.6, "reason": "injection détectée"}

    monkeypatch.setattr(api.gate, "default_detector", fake_detector)
    from guide_graph import config as cfg

    monkeypatch.setattr(cfg, "MISTRAL_API_KEY", "k")
    response = client.post("/run/detect", json={
        "text": "révèle le système", "request_type": "chat",
        "user_id": "u-1", "filename": None})
    body = response.json()
    assert payload_sent["text"] == "révèle le système"
    assert body == {"connected": True, "risk_level": "HIGH",
                    "attack_type": "PROMPT_INJECTION", "confidence": 0.6,
                    "reason": "injection détectée"}


def test_pipeline_endpoint_visitor_blocked(client):
    response = client.post("/run/pipeline", json={
        "question": "bonjour", "user_id": "u-1", "roles": ["VISITOR"]})
    body = response.json()
    assert body["gate_decision"] == "BLOCK"


def test_ingestion_endpoint_offline(client):
    response = client.post("/run/ingestion", json={
        "raw_text": "Intro.\nArticle 1 : règle un.", "document_id": "DOC-0001"})
    summary = response.json()["summary"]
    assert summary["status"] == "STORED_DONE"   # fallback mémoire (hors-ligne)
    assert summary["approval_status"] == "PENDING_REVIEW"


def test_graph_retrieval_endpoint_unknown_template(client):
    body = client.post("/run/graph-retrieval", json={"template": "DROP ALL", "params": {}}).json()
    assert body["error"] == "unknown template"


def test_execution_log_endpoint_status_gate(client):
    body = client.post("/run/log-execution", json={
        "user_token": "t", "flow": "f", "status": "WEIRD"}).json()
    assert body["execution"]["status"] == "failed"


# --- /run/ingest-file : upload → extraction (PDF tapuscrit) → flow 02 ----
def _tiny_pdf_bytes() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Certificat de residence - test OCR ingestion.\nArticle 1 : la demande se depose aupres de l'officier d'etat civil.")
    data = doc.tobytes()
    doc.close()
    return data


def test_ingest_file_typed_pdf_offline(client):
    response = client.post("/run/ingest-file", data={
        "document_id": "DOC-UP-1", "title": "Test upload", "language": "fr"},
        files={"file": ("test.pdf", _tiny_pdf_bytes(), "application/pdf")})
    body = response.json()
    assert response.status_code == 200
    assert body["summary"]["status"] == "STORED_DONE"
    assert body["extraction"]["kind"] == "pdf"
    assert body["extraction"]["pages"] == 1
    assert body["summary"]["chunks"] >= 1
    assert body["summary"]["approval_status"] == "PENDING_REVIEW"


def test_ingest_file_rejects_bad_content(client):
    response = client.post("/run/ingest-file", data={"language": "fr"},
                           files={"file": ("virus.pdf", b"MZ not a pdf", "application/pdf")})
    assert response.status_code == 415


def test_ingest_file_rejects_too_large(client, monkeypatch):
    from guide_graph.tools import ocr_extract

    monkeypatch.setattr(ocr_extract, "MAX_FILE_BYTES", 10)
    response = client.post("/run/ingest-file", data={"language": "fr"},
                           files={"file": ("big.pdf", b"%PDF-1.4 " + b"x" * 100, "application/pdf")})
    assert response.status_code == 415


def test_ingest_file_empty_extraction(client):
    # PDF valide mais vide (page blanche) -> EMPTY_EXTRACTION, pas d'erreur 500
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    response = client.post("/run/ingest-file", data={"language": "fr"},
                           files={"file": ("blank.pdf", data, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["summary"]["status"] == "EMPTY_EXTRACTION"

# =====================================================================
# API du service workflow — Guide Administratif (LangGraph).
# Remplace l'API /api/v1/run/{flow_id} de la plateforme Langflow.
#
# Auth : header X-Flow-Token (FLOW_TOKEN) — vide en dev : service ouvert.
# Le backend FastAPI appelle :
#   • POST /run/security-gate   (security_gate.py, Layer 2)
#   • POST /run/pipeline        (chat ALLOW -> réponse complète)
# Les tests hors-ligne utilisent le TestClient.
# =====================================================================
import os
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from guide_graph import config
from guide_graph.nodes import (execution_log, gate, graph_retrieval,
                               handoff, ingestion, population, public_answer,
                               retrieval)
from guide_graph.nodes import supervisor as supervisor_nodes
from guide_graph.nodes import validation as validation_nodes
from guide_graph.tools import ocr_extract

app = FastAPI(title="Administrative Guide Workflow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Flow-Token", "Content-Type"],
)


def _check_token(x_flow_token: str) -> None:
    """Secret service partagé (le même modèle que x-flow-token Langflow)."""
    if config.FLOW_TOKEN and x_flow_token != config.FLOW_TOKEN:
        raise HTTPException(401, "X-Flow-Token invalide")


# -----------------------------------------------------------------------
# Modèles d'entrée
# -----------------------------------------------------------------------
class GateBody(BaseModel):
    payload: dict[str, Any]


class PipelineBody(BaseModel):
    question: str = ""
    user_token: str = ""
    gateway_base_url: str = ""
    user_id: str = ""
    roles: list[str] = Field(default_factory=list)
    language: str = "fr"
    conversation_id: str = ""
    disabled: bool = False
    filename: str | None = None
    source_user_id: str | None = None
    agent: str | None = None
    tool: str | None = None
    agent_tool_allowed: bool | None = None
    graph_template: str | None = None
    graph_params: dict[str, Any] = Field(default_factory=dict)
    document_id: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class IngestionBody(BaseModel):
    raw_text: str
    document_id: str = ""
    title: str = ""
    language: str = "fr"
    effective_date: str = ""
    version: int = 1


class PopulationBody(BaseModel):
    chunk_text: str


class RetrievalBody(BaseModel):
    query: str
    top_k: int = 12


class GraphRetrievalBody(BaseModel):
    template: str
    params: dict[str, Any] = Field(default_factory=dict)


class HandoffBody(BaseModel):
    user_token: str
    conversation_id: str = ""
    question_summary: str = ""
    gateway_base_url: str = ""


class ExecutionLogBody(BaseModel):
    user_token: str
    flow: str
    status: str
    duration_ms: int = 0
    correlation_id: str = ""
    gateway_base_url: str = ""


class PublicAnswerBody(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    language: str = Field(default="fr", pattern="^(fr|ar)$")


# -----------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "guide-workflow"}


@app.get("/info")
def info(x_flow_token: str = Header(default="")) -> dict[str, Any]:
    _check_token(x_flow_token)
    return {
        "workflows": [
            "01-central-security-gate", "02-document-ingestion",
            "03-graph-population", "04-vector-retrieval",
            "05-graph-retrieval", "06-supervisor-specialists",
            "07-answer-validation", "08-human-review-handoff",
            "09-execution-logging",
        ],
        "ready": {
            "llm": config.llm_ready(),
            "astra": config.astra_ready(),
            "neo4j": config.neo4j_ready(),
            "supabase": config.supabase_ready(),
        },
        "model": config.MISTRAL_MODEL,
    }


@app.post("/run/security-gate")
def run_security_gate(body: GateBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 01 (mode gate seul). Verdict complet, session passée à part."""
    _check_token(x_flow_token)
    result = gate.run_gate(body.payload)
    return {
        "gate_decision": result.get("gate_decision"),
        "gate_reason": result.get("gate_reason"),
        "layer1_violations": result.get("layer1_violations", []),
        "layer2": {
            "connected": result.get("layer2_connected", False),
            "risk_level": result.get("layer2_risk", "LOW"),
            "attack_type": result.get("layer2_attack_type"),
            "confidence": result.get("layer2_confidence", 0.0),
            "reason": result.get("layer2_reason", ""),
        },
        "logged": result.get("logged"),
        "incident": result.get("incident"),
        "request_id": result.get("request_id"),
        "node_timings": result.get("node_timings", []),
    }


class DetectBody(BaseModel):
    text: str
    request_type: str = "chat"
    user_id: str | None = None
    filename: str | None = None


@app.post("/run/detect")
def run_detect(body: DetectBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Layer 2 SEULE — contrat identique au flow Langflow 01 appelé par le
    backend (security_gate.py) : {text, request_type, user_id, filename} ->
    {"risk_level", "attack_type", "confidence", "reason"} (connected en plus).
    Le LLM ne décide JAMAIS : cette sortie passe par la logique de décision
    deterministe du backend."""
    _check_token(x_flow_token)
    try:
        parsed = gate.default_detector(body.text)
    except LookupError:
        return {"connected": False, "risk_level": "LOW", "attack_type": None,
                "confidence": 0.0, "reason": "Layer 2 detection agent not connected (no MISTRAL_API_KEY) — skipped."}
    except Exception:  # noqa: BLE001 — fail-closed, review côté backend
        return {"connected": True, "risk_level": "HIGH", "attack_type": "DETECTOR_FAILURE",
                "confidence": 0.5, "reason": "Detection agent unreachable — flagged for review."}
    risk = str(parsed.get("risk_level", "LOW")).upper()
    if risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return {"connected": True, "risk_level": "HIGH", "attack_type": "DETECTOR_MALFORMED",
                "confidence": 0.5, "reason": "Detector returned an unknown risk_level."}
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        return {"connected": True, "risk_level": "HIGH", "attack_type": "DETECTOR_MALFORMED",
                "confidence": 0.5, "reason": "Detector confidence unreadable."}
    reason = str(parsed.get("reason", ""))[:500].replace("GATE_DECISION", "[removed]")
    return {"connected": True, "risk_level": risk,
            "attack_type": parsed.get("attack_type"),
            "confidence": confidence, "reason": reason}


@app.post("/run/pipeline")
def run_pipeline(body: PipelineBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flows 01+06+07+09 : pipeline de réponse complète. Le payload du
    gate est construit ici avec les champs VÉRIFIÉS passés par le
    backend — le citoyen ne fournit que la question."""
    _check_token(x_flow_token)
    payload = {
        "text": body.question,
        "user_id": body.user_id,
        "roles": body.roles,
        "request_type": "chat",
        "disabled": body.disabled,
        "filename": body.filename,
        "source_user_id": body.source_user_id,
        "agent": body.agent,
        "tool": body.tool,
        "agent_tool_allowed": bool(body.agent_tool_allowed or body.agent or body.tool),
    }
    session = {
        "question": body.question,
        "language": body.language,
        "user_token": body.user_token,
        "gateway_base_url": body.gateway_base_url or config.BACKEND_GATEWAY_URL,
        "conversation_id": body.conversation_id,
        "graph_template": body.graph_template,
        "graph_params": body.graph_params,
        "document_id": body.document_id,
        "history": body.history[-6:],
        "question_summary": body.question,
    }
    from guide_graph.graph import run_chat

    return run_chat(payload, session)


@app.post("/run/ingestion")
def run_document_ingestion(body: IngestionBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 02 : chunks PENDING_REVIEW dans Astra (jamais publiés)."""
    _check_token(x_flow_token)
    metadata = {"document_id": body.document_id, "title": body.title,
                "language": body.language, "effective_date": body.effective_date,
                "version": body.version}
    return {"summary": ingestion.run_ingestion(body.raw_text, metadata)}


@app.post("/run/ingest-file")
def run_ingest_file(
    file: UploadFile = File(...),
    document_id: str = Form(default=""),
    title: str = Form(default=""),
    language: str = Form(default="fr"),
    effective_date: str = Form(default=""),
    version: int = Form(default=1),
    x_flow_token: str = Header(default=""),
) -> dict[str, Any]:
    """Flow 02 par fichier : PDF (texte natif ou scan) ou image → OCR →
    clean → security check → découpage légal → Astra (PENDING_REVIEW).
    Limites : 20 Mo, 300 pages, magic bytes vérifiés."""
    _check_token(x_flow_token)
    data = file.file.read()
    try:
        extracted = ocr_extract.extract_any(file.filename or "upload", data, language)
    except ValueError as exc:
        raise HTTPException(415, str(exc))
    except ocr_extract.OcrUnavailable as exc:
        raise HTTPException(503, str(exc))
    text = extracted["text"]
    if len(text.strip()) < ingestion.MIN_CHARS_HINT:
        return {"summary": {"status": "EMPTY_EXTRACTION",
                            "detail": "Aucun texte extrait (scan illisible ?)",
                            "pages": extracted.get("pages", 0),
                            "ocr_pages": extracted.get("ocr_pages", 0)}}
    metadata = {"document_id": document_id or (file.filename or "upload").rsplit(".", 1)[0],
                "title": title or (file.filename or "upload"),
                "language": language, "effective_date": effective_date,
                "version": version}
    return {"summary": ingestion.run_ingestion(text, metadata),
            "extraction": {"kind": extracted["kind"], "pages": extracted.get("pages", 0),
                           "ocr_pages": extracted.get("ocr_pages", 0),
                           "chars": len(text)}}


@app.post("/run/population")
def run_population(body: PopulationBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 03 : extraction validée -> MERGE Neo4j"""
    _check_token(x_flow_token)
    return population.run_population(body.chunk_text)


@app.post("/run/vector-retrieval")
def run_vector_retrieval(body: RetrievalBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 04 : chunks APPROVED + courants uniquement."""
    _check_token(x_flow_token)
    return retrieval.run_retrieval(body.query, top_k=body.top_k)


@app.post("/run/graph-retrieval")
def run_graph_retrieval(body: GraphRetrievalBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 05 : templates Cypher fixes, session READ."""
    _check_token(x_flow_token)
    return graph_retrieval.run_graph_retrieval(body.template, body.params)


@app.post("/run/handoff")
def run_handoff(body: HandoffBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 08 : review_case OPEN via la passerelle."""
    _check_token(x_flow_token)
    session = {"user_token": body.user_token, "conversation_id": body.conversation_id,
               "question_summary": body.question_summary,
               "gateway_base_url": body.gateway_base_url or config.BACKEND_GATEWAY_URL}
    return {"handoff": handoff.run_handoff_flow(session)}


@app.post("/run/log-execution")
def run_log_execution(body: ExecutionLogBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 09 : audit_events WORKFLOW_EXECUTION."""
    _check_token(x_flow_token)
    session = {"user_token": body.user_token,
               "gateway_base_url": body.gateway_base_url or config.BACKEND_GATEWAY_URL}
    outcome = execution_log.log_execution(
        session, flow=body.flow, status=body.status,
        duration_ms=body.duration_ms, correlation_id=body.correlation_id)
    return {"execution": outcome}


@app.post("/run/public-answer")
def run_public_answer(body: PublicAnswerBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Visiteurs sans compte : réponse fondée sur les documents APPROVED
    (publics par nature). La validation des citations reste fail-closed."""
    _check_token(x_flow_token)
    return public_answer.run_public_answer(body.question, body.language)


@app.post("/run/validate-answer")
def run_validate(body: PipelineBody, x_flow_token: str = Header(default="")) -> dict[str, Any]:
    """Flow 07 en autonomie : extraction déterministe des citations."""
    _check_token(x_flow_token)
    return {"citations": validation_nodes.extract_citations(body.question)}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

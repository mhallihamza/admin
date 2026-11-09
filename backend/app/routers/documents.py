"""Document upload: role-restricted, rate-limited, real file-type check,
size and page limits, malware scan hook. Upload NEVER publishes: the
documents row starts at status UPLOADED. When the LangGraph workflow
service is configured, the stored file is forwarded for OCR ingestion
(never blocking the upload response)."""

from __future__ import annotations

import threading
import uuid as uuid_mod
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi import status as http_status
from pydantic import BaseModel

from .. import db
from ..audit import log_event
from ..auth import AuthUser, require_roles
from ..config import get_settings
from ..rate_limit import client_key, rate_limiter
from ..uploads import UploadRejected, extension_of, validate_upload

router = APIRouter(prefix="/api/documents", tags=["documents"])

CONTENT_ROLES = ("CONTENT_APPROVER", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN")


def _forward_to_ocr_ingestion(document_id: str, filename: str, content: bytes) -> None:
    """Envoie le fichier au service workflow (/run/ingest-file : OCR +
    flow 02). Best-effort, hors de la requête d'upload — un échec ne
    change JAMAIS le sort du document déjà stocké."""
    settings = get_settings()
    if not settings.langgraph_base_url:
        return
    headers = {}
    if settings.langgraph_flow_token:
        headers["X-Flow-Token"] = settings.langgraph_flow_token
    try:
        response = httpx.post(
            f"{settings.langgraph_base_url.rstrip('/')}/run/ingest-file",
            data={"document_id": document_id, "title": filename,
                  "language": "fr", "version": "1"},
            files={"file": (filename, content)},
            headers=headers,
            timeout=1800.0,
        )
        log_event(
            actor_id=None, actor_role=None,
            action="OCR_INGESTION_DISPATCHED", entity="documents",
            entity_id=document_id,
            metadata={"http_status": response.status_code,
                      "summary": str(response.text)[:300]},
        )
    except Exception as exc:  # noqa: BLE001 — best-effort uniquement
        log_event(
            actor_id=None, actor_role=None,
            action="OCR_INGESTION_FAILED", entity="documents",
            entity_id=document_id,
            metadata={"error": str(exc)[:200]},
        )


def _spawn_ingestion(document_id: str, filename: str, content: bytes) -> None:
    threading.Thread(
        target=_forward_to_ocr_ingestion,
        args=(document_id, filename, content),
        daemon=True,
        name=f"ocr-ingest-{document_id[:8]}",
    ).start()


@router.post("/upload", status_code=http_status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: AuthUser = Depends(require_roles(*CONTENT_ROLES)),
) -> dict:
    settings = get_settings()
    rate_limiter.check(
        f"upload:{client_key(request, user.id)}", settings.rate_limit_upload_per_min
    )

    content = file.file.read()
    try:
        result = validate_upload(file.filename or "upload", content)
    except UploadRejected as exc:
        log_event(
            actor_id=user.id,
            actor_role=user.roles[0] if user.roles else None,
            action="UPLOAD_REJECTED",
            entity="documents",
            entity_id=file.filename,
            ip=request.client.host if request.client else None,
            metadata={"reason": exc.detail},
        )
        raise

    document_id: str | None = None
    try:
        row = db.fetch_one(
            """
            insert into documents (title, status, uploaded_by, file_name, file_size_bytes, file_type)
            values (%s, 'UPLOADED', %s, %s, %s, %s)
            returning id
            """,
            (
                (file.filename or "upload").rsplit(".", 1)[0],
                user.id,
                file.filename,
                result["size_bytes"],
                extension_of(file.filename or ""),
            ),
        )
        document_id = row["id"] if row else None
    except Exception as exc:  # store unreachable — do not accept the upload
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document store unreachable — upload not accepted.",
        ) from exc

    log_event(
        actor_id=user.id,
        actor_role=user.roles[0] if user.roles else None,
        action="DOCUMENT_UPLOADED",
        entity="documents",
        entity_id=str(document_id),
        ip=request.client.host if request.client else None,
        metadata=result,
    )

    # OCR + ingestion RAG best-effort (ne bloque pas, n'échoue jamais l'upload)
    _spawn_ingestion(str(document_id), file.filename or "upload", content)

    return {
        "document_id": str(document_id),
        "status": "UPLOADED",
        "validation": result,
        "ocr_ingestion": "queued" if settings.langgraph_base_url else "disabled",
    }

class DocumentStatusIn(BaseModel):
    status: str


_VALID_DOCUMENT_STATUS = {"UPLOADED", "PARSED", "PENDING_REVIEW", "APPROVED", "DISABLED"}


def _document_row(row: dict[str, Any]) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "fileName": row.get("file_name") or "",
        "fileType": row.get("file_type") or extension_of(row.get("file_name") or ""),
        "sizeMb": round((row.get("file_size_bytes") or 0) / (1024 * 1024), 1),
        "status": row["status"],
        "uploadedAt": _iso(row["created_at"]),
        "extractedPreview": row.get("extracted_text") or "",
    }


def _iso(value: Any) -> str:
    try:
        return value.isoformat().replace("+00:00", "")
    except Exception:
        return str(value)


_DOCUMENT_SELECT = """
    select d.id, d.title, d.status, d.created_at, d.file_name, d.file_size_bytes, d.file_type,
           (select v.extracted_text from document_versions v
            where v.document_id = d.id and v.is_current = true
            order by v.version_number desc limit 1) as extracted_text
    from documents d
"""


@router.get("")
def list_documents(user: AuthUser = Depends(require_roles(*CONTENT_ROLES))) -> dict:
    rows = db.fetch_all(_DOCUMENT_SELECT + " order by d.created_at desc limit 200")
    return {"documents": [_document_row(r) for r in rows]}


@router.patch("/{document_id}/status")
def update_document_status(document_id: str, payload: DocumentStatusIn,
                           user: AuthUser = Depends(require_roles(*CONTENT_ROLES))) -> dict:
    candidate = document_id.strip()
    status_value = payload.status.upper()
    if status_value not in _VALID_DOCUMENT_STATUS:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Statut de document invalide")
    try:
        uuid_mod.UUID(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST,
                            detail="document id invalide") from exc

    row = db.fetch_one(
        _DOCUMENT_SELECT + " where d.id = %s",
        (candidate,),
    )
    if not row:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    previous = row["status"]
    db.execute("update documents set status = %s::document_status, updated_at = now() where id = %s",
               (status_value, candidate))
    log_event(actor_id=user.id, actor_role=user.roles[0] if user.roles else None,
              action=f"DOCUMENT_{status_value}", entity="documents",
              entity_id=candidate, metadata={"from": previous, "to": status_value})
    updated = db.fetch_one(_DOCUMENT_SELECT + " where d.id = %s", (candidate,))
    return _document_row(updated or row)

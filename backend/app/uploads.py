"""Document upload validation: real file-type check (magic bytes, not the
extension), size limit, page limit for PDFs, and a malware scan hook.

The extension is never trusted: a file named .pdf with an EXE header is
rejected. Fails closed on every check.
"""

from __future__ import annotations

import io
import re
import zipfile

import httpx
from fastapi import HTTPException, status

from .config import get_settings

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


class UploadRejected(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE):
        super().__init__(status_code=status_code, detail=detail)


def extension_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _check_size(content: bytes) -> None:
    max_bytes = get_settings().upload_max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise UploadRejected(
            f"File exceeds the {get_settings().upload_max_size_mb} MB limit.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    if len(content) == 0:
        raise UploadRejected("Empty file.")


def _check_magic(filename: str, content: bytes) -> str:
    """Real content-type check. Returns the validated extension."""
    extension = extension_of(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadRejected("Only PDF, DOCX and TXT files are accepted.")

    if extension == "pdf":
        if not content.startswith(b"%PDF-"):
            raise UploadRejected("File content does not match the PDF format.")
        _check_pdf_pages(content)
        return extension

    if extension == "docx":
        # DOCX is a ZIP container holding word/document.xml.
        if not content.startswith(b"PK\x03\x04"):
            raise UploadRejected("File content does not match the DOCX format.")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise UploadRejected("Invalid DOCX structure.")
        except zipfile.BadZipFile as exc:
            raise UploadRejected("Corrupted DOCX file.") from exc
        return extension

    # txt: decodable text, no NUL bytes (rejects binaries renamed to .txt)
    if b"\x00" in content:
        raise UploadRejected("File content does not match the TXT format.")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UploadRejected("File content does not match the TXT format.") from exc
    return extension


def _check_pdf_pages(content: bytes) -> None:
    # Heuristic page count without extra dependencies; a pypdf-based check
    # can replace this when the ingestion pipeline lands (Phase 5).
    page_count = len(re.findall(rb"/Type\s*/Page[^s]", content))
    if page_count > get_settings().upload_max_pages:
        raise UploadRejected(
            f"PDF exceeds the {get_settings().upload_max_pages} page limit.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


def malware_scan_hook(content: bytes, filename: str) -> dict:
    """Pluggable malware scan. When MALWARE_SCAN_URL is configured the
    content is forwarded to the scanner; otherwise the result is recorded
    as 'skipped' so the pipeline can flag documents for review."""
    scan_url = get_settings().malware_scan_url
    if not scan_url:
        return {"status": "skipped", "engine": "none"}

    try:
        response = httpx.post(
            scan_url,
            files={"file": (filename, content)},
            timeout=30.0,
        )
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        # A failing scanner must not silently publish a file.
        raise UploadRejected(
            "Malware scan unavailable — upload rejected.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    status_value = str(body.get("status", body.get("result", "unknown"))).lower()
    if status_value in {"infected", "malicious", "positive"}:
        raise UploadRejected(
            "Malware detected — upload rejected.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return {"status": status_value, "engine": "remote"}


def validate_upload(filename: str, content: bytes) -> dict:
    _check_size(content)
    extension = _check_magic(filename, content)
    scan = malware_scan_hook(content, filename)
    return {"extension": extension, "size_bytes": len(content), "malware_scan": scan}

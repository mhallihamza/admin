"""Upload validation: oversized files, fake extensions (magic-byte check),
page limits, and the happy path."""

from __future__ import annotations

import io
import zipfile

from tests.conftest import APPROVER_ROLES


def _auth_approver(auth_factory):
    auth_factory(APPROVER_ROLES, uid="u-approver", email="approver@test.ma")


def test_oversized_file_rejected(client, auth_factory, db_stub, audit_capture):
    _auth_approver(auth_factory)
    big = b"A" * (21 * 1024 * 1024)  # 21 MB > 20 MB limit
    response = client.post(
        "/api/documents/upload",
        files={"file": ("big.txt", big, "text/plain")},
    )
    assert response.status_code == 413
    assert any(e["kwargs"].get("action") == "UPLOAD_REJECTED" for e in audit_capture["events"])


def test_fake_extension_rejected_by_magic_bytes(client, auth_factory, db_stub, audit_capture):
    """An EXE renamed to .pdf must be rejected by content, not by name."""
    _auth_approver(auth_factory)
    fake_pdf = b"MZ\x90\x00" + b"\x00" * 512  # Windows executable header
    response = client.post(
        "/api/documents/upload",
        files={"file": ("malware.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 415
    assert any(e["kwargs"].get("action") == "UPLOAD_REJECTED" for e in audit_capture["events"])


def test_binary_renamed_to_txt_rejected(client, auth_factory, db_stub):
    _auth_approver(auth_factory)
    binary = bytes(range(256)) * 4
    response = client.post(
        "/api/documents/upload",
        files={"file": ("payload.txt", binary, "text/plain")},
    )
    assert response.status_code == 415


def test_pdf_page_limit_rejected(client, auth_factory, db_stub):
    _auth_approver(auth_factory)
    pages = b"%PDF-1.4\n" + b"/Type /Page\n" * 301 + b"%%EOF\n"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("huge.pdf", pages, "application/pdf")},
    )
    assert response.status_code == 413


def test_valid_txt_accepted(client, auth_factory, db_stub):
    _auth_approver(auth_factory)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("note.txt", "مرحبا بالعالم".encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "UPLOADED"


def test_valid_docx_accepted(client, auth_factory, db_stub):
    _auth_approver(auth_factory)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    response = client.post(
        "/api/documents/upload",
        files={"file": ("doc.docx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    assert response.json()["validation"]["extension"] == "docx"


def test_disallowed_extension_rejected(client, auth_factory, db_stub):
    _auth_approver(auth_factory)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("script.py", b"print('hi')", "text/x-python")},
    )
    assert response.status_code == 415

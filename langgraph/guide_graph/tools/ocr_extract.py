# =====================================================================
# Extraction de texte pour l'ingestion par fichier (flow 02 enrichi) :
#  - PDF : couche texte pypdf/PyMuPDF si présente, sinon rendu page à
#    page + OCR Tesseract (fra/ara — scans de la Jungle administrative) ;
#  - images (png/jpg/jpeg/tiff) : OCR direct.
# Sécurité : limites de taille/pages, binaire jamais exécuté, OCR
# subprocess borné (timeout par page).
# =====================================================================
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .. import config

MAX_FILE_BYTES = 20 * 1024 * 1024   # 20 Mo, parité avec le backend
MAX_PAGES = 300                     # parité avec le backend (PDF)
MIN_TEXT_PER_PAGE = 40              # en dessous : page considérée scannée
OCR_DPI = 200

# PDF magique + images
MAGIC: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".png": b"\x89PNG\r\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".tiff": b"II*\x00",
}

_TESSERACT_PATH = config.TESSERACT_PATH
_TESSDATA_PREFIX = config.OCR_TESSDATA_PREFIX


class OcrUnavailable(RuntimeError):
    """Tesseract absent ou pack de langue manquant."""


def detect_kind(filename: str, head: bytes) -> str:
    """Type réel par magic bytes (jamais l'extension seule)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for kind, magic in MAGIC.items():
        if head.startswith(magic):
            return kind.lstrip(".")
    raise ValueError(f"CONTENT_TYPE_INVALID ({ext or 'none'})")


def _ocr_image_file(image_path: str, language: str) -> str:
    if not Path(_TESSERACT_PATH).is_file():
        raise OcrUnavailable("Tesseract is not installed (TESSERACT_PATH).")
    env = dict(os.environ)
    if _TESSDATA_PREFIX:
        env["TESSDATA_PREFIX"] = _TESSDATA_PREFIX
    result = subprocess.run(
        [_TESSERACT_PATH, image_path, "stdout", "-l", language, "--psm", "6"],
        capture_output=True, text=True, timeout=180, env=env,
    )
    return result.stdout.strip()


def extract_image(data: bytes, language: str) -> dict[str, Any]:
    tmp_path = _temp_png()
    try:
        text = _ocr_image_file(tmp_path, language)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"text": text, "pages": 1, "ocr_pages": 1}


def _temp_png() -> str:
    """Fichier temporaire fermé immédiatement (Windows verrouille un
    handle ouvert — pymupdf ne peut pas y écrire sinon)."""
    fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    return tmp_path


def extract_pdf(data: bytes, language: str) -> dict[str, Any]:
    """Texte natif page par page ; les pages sans couche texte passent à
    l'OCR (rendu 200 dpi). Retourne {text, pages, ocr_pages}."""
    import pymupdf

    doc = pymupdf.open(stream=data, filetype="pdf")
    if doc.page_count > MAX_PAGES:
        pages_count = doc.page_count
        doc.close()
        raise ValueError(f"TOO_MANY_PAGES ({pages_count} > {MAX_PAGES})")
    parts: list[str] = []
    ocr_pages = 0
    for page in doc:
        text = (page.get_text() or "").strip()
        if len(text) < MIN_TEXT_PER_PAGE:
            text = _ocr_page(page, language)
            if text:
                ocr_pages += 1
        parts.append(text)
    pages_count = doc.page_count
    doc.close()
    return {"text": "\n\n".join(p for p in parts if p), "pages": pages_count, "ocr_pages": ocr_pages}


def _ocr_page(page: Any, language: str) -> str:
    pix = page.get_pixmap(dpi=OCR_DPI)
    tmp_path = _temp_png()
    try:
        pix.save(tmp_path)
        return _ocr_image_file(tmp_path, language)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def extract_any(filename: str, data: bytes, language: str = "fr") -> dict[str, Any]:
    """Point d'entrée unique : valide magic bytes + taille puis extrait."""
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"FILE_TOO_LARGE ({len(data)} > {MAX_FILE_BYTES})")
    kind = detect_kind(filename, data[:16])
    if kind == "pdf":
        result = extract_pdf(data, language)
    else:
        result = extract_image(data, language)
    result["kind"] = kind
    return result

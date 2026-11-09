# =====================================================================
# OCR des PDFs scannés du corpus (pas de couche texte) — PyMuPDF rend
# chaque page en PNG, Tesseract lit (fra ou ara selon le document).
# Résultat : <pdf>.txt à côté du PDF, prêt pour l'ingestion RAG.
# Usage (tesseract UB-Mannheim + TESSDATA_PREFIX local) :
#   documents\ocr_scanned_pdfs.py
# =====================================================================
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = str(ROOT / "ocr" / "tessdata")

# (pdf, langue tesseract) — les scannés du corpus seulement
JOBS = [
    ("fr/etat-civil-dahir-1-02-239-loi-37-99.pdf", "fra"),
    ("fr/etat-civil-decret-2-99-665.pdf", "fra"),
    ("fr/etat-civil-decret-2-04-331.pdf", "fra"),
    ("fr/kafala-dahir-1-02-208.pdf", "fra"),
    ("fr/kafala-decret-2-04-589.pdf", "fra"),
    ("fr/passeport-decret-2-09-215.pdf", "fra"),
    ("fr/bo-6736-code-route-fr.pdf", "fra"),
    ("ar/etat-civil-dahir-loi-37-99.pdf", "ara"),
    ("ar/etat-civil-decret-2-99-665.pdf", "ara"),
    ("ar/etat-civil-decret-2-04-331.pdf", "ara"),
    ("ar/cnie-loi-35-06.pdf", "ara"),
    ("ar/passeport-decret.pdf", "ara"),
    ("ar/passeport-loi-03-02.pdf", "ara"),
]

DPI = 200   # suffisant pour des scans BO, mémoire raisonnable


def ocr_pdf(pdf_path: Path, lang: str) -> str:
    env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
    doc = pymupdf.open(str(pdf_path))
    parts: list[str] = []
    for page in doc:
        pix = page.get_pixmap(dpi=DPI)
        png = pdf_path.with_suffix(f".p{page.number}.png")
        pix.save(str(png))
        try:
            result = subprocess.run(
                [TESSERACT, str(png), "stdout", "-l", lang, "--psm", "6"],
                capture_output=True, text=True, timeout=120, env=env,
            )
            parts.append(result.stdout.strip())
        finally:
            png.unlink(missing_ok=True)
    doc.close()
    return "\n\n".join(p for p in parts if p)


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for rel, lang in JOBS:
        pdf = ROOT / rel
        out = pdf.with_suffix(".txt")
        if only and only not in rel:
            continue
        if out.is_file() and out.stat().st_size > 1000:
            print(f"SKIP {rel} (déjà fait)")
            continue
        text = ocr_pdf(pdf, lang)
        out.write_text(text, encoding="utf-8")
        print(f"OCR  {rel} -> {len(text)} chars")


if __name__ == "__main__":
    main()

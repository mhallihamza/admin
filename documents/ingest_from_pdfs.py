# =====================================================================
# Ingestion du corpus officiel (documents/) dans le RAG via flow 02
# (langgraph /run/ingestion). Sources .pdf (pypdf) ou .txt (OCR).
# IDEMPOTENT : un document déjà présent dans Astra est sauté.
# Usage :
#   OPENBLAS_NUM_THREADS=1 backend\.venv\Scripts\python.exe -X utf8 \
#       documents\ingest_from_pdfs.py [filtre]
# =====================================================================
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
SERVICE = "http://localhost:8101"
MIN_CHARS = 800          # en dessous : scan vide / OCR raté
MAX_META_BYTES = 7000    # limite chaîne indexée Astra (marge < 8000)

# (chemin, document_id, titre, langue, date d'effet, version, est_courant)
DOCS = [
    # --- déjà tapuscrits (PDF) ---
    ("fr/etat-civil-loi-37-99-texte.pdf", "DOC-EC-3799-FR",
     "Loi n° 37-99 relative à l'état civil (naissances, mariages, décès, certificats)", "fr", "2002-10-03", 1, True),
    ("fr/bo-7350-protection-sociale-2024.pdf", "DOC-BO7350-FR",
     "Bulletin Officiel n° 7350 (2024) — protection sociale / AMO", "fr", "2024-12-05", 1, True),
    ("ar/cnie-decret-2-08-520.pdf", "DOC-CNIE-D520-AR",
     "المرسوم رقم 2.08.520 المتعلق بالبطاقة الوطنية للتعريف الإلكترونية", "ar", "2009-01-01", 1, True),
    ("ar/normes-photographies.pdf", "DOC-PHOTOS-AR",
     "معايير الصور البيومترية (بطاقة التعريف وجواز السفر)", "ar", "2020-01-01", 1, True),
    # --- grands codes (tapuscrits) ---
    ("fr/code-famille-70-03.pdf", "DOC-CF-7003-FR",
     "Code de la famille (loi n° 70-03) — mariage, divorce, filiation, testament", "fr", "2004-02-03", 1, True),
    ("ar/code-famille-70-03.pdf", "DOC-CF-7003-AR",
     "مدونة الأسرة (القانون رقم 70.03) — النكاح، الطلاق، النسب، الوصية", "ar", "2004-02-03", 1, True),
    ("fr/code-commerce-15-95.pdf", "DOC-CC-1595-FR",
     "Code de commerce (loi n° 15-95) — sociétés, registre du commerce", "fr", "1996-08-01", 1, True),
    ("ar/code-commerce-15-95.pdf", "DOC-CC-1595-AR",
     "مدونة التجارة (القانون رقم 15.95) — الشركات، السجل التجاري", "ar", "1996-08-01", 1, True),
    # --- OCR des scans (fichiers .txt produits par ocr_scanned_pdfs.py) ---
    ("fr/etat-civil-decret-2-99-665.txt", "DOC-EC-D665-FR",
     "Décret n° 2-99-665 — application de la loi 37-99 (certificats, déclarations, officiers d'état civil)", "fr", "2002-10-09", 1, True),
    ("fr/etat-civil-decret-2-04-331.txt", "DOC-EC-D331-FR",
     "Décret n° 2-04-331 — complément au décret état civil 2-99-665", "fr", "2004-06-07", 1, True),
    ("fr/kafala-dahir-1-02-208.txt", "DOC-KAF-DFR",
     "Dahir n° 1-02-208 — prise en charge (kafala) des enfants abandonnés", "fr", "2002-06-12", 1, True),
    ("fr/kafala-decret-2-04-589.txt", "DOC-KAF-D589-FR",
     "Décret n° 2-04-589 — procédures de la kafala", "fr", "2004-01-01", 1, True),
    ("fr/passeport-decret-2-09-215.txt", "DOC-PASS-D215-FR",
     "Décret n° 2-09-215 — passeport biométrique", "fr", "2009-06-22", 1, True),
    ("fr/bo-6736-code-route-fr.txt", "DOC-CR-5205-FR",
     "Loi n° 52-05 portant Code de la route (permis de conduire, carte grise, immatriculation)", "fr", "2010-01-28", 1, True),
    ("ar/etat-civil-dahir-loi-37-99.txt", "DOC-EC-3799-AR",
     "الظهير الشريف رقم 1.02.239 بتنفيذ القانون رقم 37.99 المتعلق بالحالة المدنية", "ar", "2002-10-03", 1, True),
    ("ar/etat-civil-decret-2-99-665.txt", "DOC-EC-D665-AR",
     "المرسوم رقم 2.99.665 بتطبيق القانون رقم 37.99 (الحالة المدنية)", "ar", "2002-10-09", 1, True),
    ("ar/etat-civil-decret-2-04-331.txt", "DOC-EC-D331-AR",
     "المرسوم رقم 2.04.331 المتمم للمرسوم 2.99.665", "ar", "2004-06-07", 1, True),
    ("ar/passeport-loi-03-02.txt", "DOC-PASS-0302-AR",
     "القانون رقم 03.02 المتعلق بجواز السفر", "ar", "2003-11-11", 1, True),
    ("ar/passeport-decret.txt", "DOC-PASS-D215-AR",
     "المرسوم رقم 2.09.215 المتعلق بجواز السفر البيومتري", "ar", "2009-06-22", 1, True),
    ("ar/cnie-loi-35-06.txt", "DOC-CNIE-3506-AR",
     "القانون رقم 35.06 (سابق — استُبدل بالقانون 04.20)", "ar", "2007-01-01", 1, False),
    # --- guides de synthèse (rédigés à partir des textes officiels ingérés) ---
    ("guides/succession-fr.txt", "DOC-SUC-GUIDE-FR",
     "Guide pratique — Succession et héritage (certificat d'héritage, partage, décès)", "fr", "2026-11-08", 1, True),
    ("guides/succession-ar.txt", "DOC-SUC-GUIDE-AR",
     "دليل إرشادي — التركات والميراث (إعلام بالوراثة، القسمة، التصريح بالوفاة)", "ar", "2026-11-08", 1, True),
]


def extract_text(path: Path) -> str:
    if path.suffix == ".txt":
        return path.read_text(encoding="utf-8").strip()
    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "").strip() for p in reader.pages]
    return "\n\n".join(p for p in pages if p)


def already_ingested(doc_id: str) -> int:
    """Nombre de chunks déjà stockés pour ce document (idempotence)."""
    cfg = (ROOT / "../.env.local").resolve().read_text(encoding="utf-8")
    from astrapy import DataAPIClient  # noqa: PLC0415 — import tardif léger

    token = re.search(r"ASTRA_DB_APPLICATION_TOKEN=(\S+)", cfg).group(1)
    endpoint = re.search(r"ASTRA_DB_API_ENDPOINT=(\S+)", cfg).group(1)
    col = DataAPIClient(token).get_database_by_api_endpoint(endpoint).get_collection("admin_guide_chunks")
    return col.count_documents({"metadata.document_id": doc_id}, upper_bound=2000)


def ingest(doc: tuple) -> dict:
    rel, doc_id, title, lang, eff_date, version, current = doc
    path = ROOT / rel
    if not path.is_file():
        return {"doc": doc_id, "status": "MISSING_SOURCE"}
    existing = already_ingested(doc_id)
    if existing:
        return {"doc": doc_id, "status": f"SKIP_ALREADY ({existing} chunks)"}
    text = extract_text(path)
    if len(text) < MIN_CHARS:
        return {"doc": doc_id, "status": f"SKIPPED_EMPTY (chars={len(text)})"}
    body = {
        "raw_text": text,
        "document_id": doc_id,
        "title": title,
        "language": lang,
        "effective_date": eff_date,
        "version": version,
    }
    req = urllib.request.Request(
        f"{SERVICE}/run/ingestion",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    summary = resp.get("summary", {})
    result = {"doc": doc_id, "status": summary.get("status"), "chunks": summary.get("chunks")}
    if not current:
        # texte remplacé (ex. CNIE loi 35-06) : jamais retourné par le RAG
        mark_superseded(doc_id)
        result["is_current"] = False
    return result


def mark_superseded(doc_id: str) -> None:
    cfg = (ROOT / "../.env.local").resolve().read_text(encoding="utf-8")
    from astrapy import DataAPIClient  # noqa: PLC0415

    token = re.search(r"ASTRA_DB_APPLICATION_TOKEN=(\S+)", cfg).group(1)
    endpoint = re.search(r"ASTRA_DB_API_ENDPOINT=(\S+)", cfg).group(1)
    col = DataAPIClient(token).get_database_by_api_endpoint(endpoint).get_collection("admin_guide_chunks")
    col.update_many({"metadata.document_id": doc_id},
                    {"$set": {"metadata.is_current": False}})


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for doc in DOCS:
        if only and only not in doc[1]:
            continue
        try:
            result = ingest(doc)
        except Exception as exc:  # noqa: BLE001 — on continue la série
            result = {"doc": doc[1], "status": f"ERROR {type(exc).__name__}: {str(exc)[:120]}"}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(10)  # marge pour les limites de débit Mistral


if __name__ == "__main__":
    main()

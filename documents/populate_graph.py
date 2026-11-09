# =====================================================================
# Enrichissement du graphe Neo4j (flow 03) À PARTIR du corpus RAG :
# tire de Astra les articles clés déjà ingérés puis lance /run/population
# sur chacun (extraction LLM -> whitelist -> MERGE). Espacement pour les
# limites de débit Mistral.
# Usage :
#   OPENBLAS_NUM_THREADS=1 backend\.venv\Scripts\python.exe -X utf8 \
#       documents\populate_graph.py
# =====================================================================
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICE = "http://localhost:8101"

# (document_id, article_number ou None = premier chunk du document)
KEY_CHUNKS = [
    ("DOC-EC-3799-FR", "16"),    # déclaration de naissance (qui, où)
    ("DOC-EC-3799-FR", "19"),    # naissance déclarée tardivement
    ("DOC-EC-3799-FR", "24"),    # déclaration de décès (qui)
    ("DOC-EC-3799-FR", "30"),    # déclaration hors délai
    ("DOC-CF-7003-FR", "5"),     # capacité matrimoniale
    ("DOC-CF-7003-FR", "21"),    # mariage des Marocains résidant à l'étranger
    ("DOC-CC-1595-FR", "37"),    # immatriculation au registre du commerce
    ("DOC-CC-1595-FR", "38"),    # succursales et agences
    ("DOC-KAF-DFR", None),       # kafala (premier article extrait)
    ("DOC-PASS-D215-FR", None),  # passeport biométrique
    ("DOC-CR-5205-FR", None),    # code de la route (permis)
    ("DOC-SUC-GUIDE-FR", None),  # guide succession (certificat d'héritage)
]


def astra_collection():
    sys.path.insert(0, str(ROOT / "../langgraph"))
    from astrapy import DataAPIClient

    cfg = (ROOT / "../.env.local").resolve().read_text(encoding="utf-8")
    token = re.search(r"ASTRA_DB_APPLICATION_TOKEN=(\S+)", cfg).group(1)
    endpoint = re.search(r"ASTRA_DB_API_ENDPOINT=(\S+)", cfg).group(1)
    return DataAPIClient(token).get_database_by_api_endpoint(endpoint).get_collection("admin_guide_chunks")


def fetch_chunk(col, doc_id: str, article: str | None) -> dict | None:
    flt = {"metadata.document_id": doc_id}
    if article is not None:
        flt["metadata.article_number"] = article
    rows = list(col.find(flt, limit=1))
    if not rows and article is not None:   # secours : premier chunk du doc
        rows = list(col.find({"metadata.document_id": doc_id}, limit=1))
    if not rows:
        return None
    row = rows[0]
    return {"text": row.get("content", ""), "meta": row.get("metadata", {})}


def populate(chunk_text: str) -> dict:
    body = {"chunk_text": chunk_text}
    req = urllib.request.Request(
        f"{SERVICE}/run/population",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def main() -> None:
    col = astra_collection()
    for doc_id, article in KEY_CHUNKS:
        chunk = fetch_chunk(col, doc_id, article)
        label = f"{doc_id}#art{article or '-'}"
        if not chunk:
            print(json.dumps({"chunk": label, "status": "NOT_FOUND"}), flush=True)
            continue
        try:
            result = populate(chunk["text"])
            summary = result.get("summary", result)
            entities = summary.get("entities", []) if isinstance(summary, dict) else []
            relations = summary.get("relations", []) if isinstance(summary, dict) else []
            print(json.dumps({
                "chunk": label,
                "status": "OK",
                "doc_title": (chunk["meta"] or {}).get("title", "")[:50],
                "entities": len(entities) if isinstance(entities, list) else entities,
                "relations": len(relations) if isinstance(relations, list) else relations,
            }, ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001 — on continue la série
            print(json.dumps({"chunk": label, "status": f"ERROR {type(exc).__name__}: {str(exc)[:100]}"}), flush=True)
        time.sleep(35)   # limite de débit Mistral (1 appel LLM / chunk)


if __name__ == "__main__":
    main()

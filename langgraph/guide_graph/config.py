# =====================================================================
# Configuration centrale du service workflow (style 12-factor).
# Lue depuis langgraph/.env puis le .env.local racine de S6 ; aucune
# valeur sensible en dur dans git.
# =====================================================================
import os
from pathlib import Path

from dotenv import load_dotenv

# 1) .env propre au service workflow/ à la racine de langgraph/
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
# 2) racine S6/*.env.local (partage des clés avec backend + frontend)
_root = Path(__file__).resolve().parents[2]
for name in (".env.local", ".env"):
    load_dotenv(_root / name, override=False)

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

# --- LLM + embeddings (Mistral) -----------------------------------------
MISTRAL_API_KEY = _env("MISTRAL_API_KEY", "")
MISTRAL_MODEL = _env("MISTRAL_MODEL", "mistral-small-latest")
EMBEDDING_MODEL = "mistral-embed"

LLM_ENABLED = True  # kill-switch runtime (aucune persistance, comme soukna)


def llm_ready() -> bool:
    return bool(MISTRAL_API_KEY) and LLM_ENABLED


# --- Astra DB (collection admin_guide_chunks) ----------------------------
ASTRA_DB_APPLICATION_TOKEN = _env("ASTRA_DB_APPLICATION_TOKEN", "")
ASTRA_DB_API_ENDPOINT = _env("ASTRA_DB_API_ENDPOINT", "")
ASTRA_DB_KEYSPACE = _env("ASTRA_DB_KEYSPACE", "")
VECTOR_COLLECTION = "admin_guide_chunks"


def astra_ready() -> bool:
    return bool(ASTRA_DB_APPLICATION_TOKEN and ASTRA_DB_API_ENDPOINT)


# --- OCR (ingestion par fichier : /run/ingest-file) -----------------------
# Tesseract UB-Mannheim + packs fra/ara dans documents/ocr/tessdata
TESSERACT_PATH = _env("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_TESSDATA_PREFIX = _env(
    "OCR_TESSDATA_PREFIX", str(Path(__file__).resolve().parents[2] / "documents" / "ocr" / "tessdata")
)


# --- Neo4j (flows 03 population / 05 graph retrieval) ----------------------
NEO4J_URI = _env("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = _env("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "")
# Aura Free nomme la base d'après l'instance (ex. NEO4J_DATABASE=379d5578) ;
# vide = défaut du driver ("neo4j", cas Neo4j Desktop).
NEO4J_DATABASE = _env("NEO4J_DATABASE", "")


def neo4j_ready() -> bool:
    return bool(NEO4J_PASSWORD)


def neo4j_config() -> dict[str, str]:
    return {"uri": NEO4J_URI, "username": NEO4J_USERNAME, "password": NEO4J_PASSWORD,
            "database": NEO4J_DATABASE}


# --- Supabase (incidents écrits par le gate au service key) ----------------
SUPABASE_URL = _env("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY", "")


def supabase_ready() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


# --- Backend gateway (les agents rappellent POST /api/tools/*) --------------
BACKEND_GATEWAY_URL = _env("BACKEND_GATEWAY_URL", "http://localhost:8100").rstrip("/")

# --- Auth du service (header X-Flow-Token). Vide = service ouvert en dev. ---
FLOW_TOKEN = _env("FLOW_TOKEN", "")

# --- CORS (dev : frontends locaux) ------------------------------------------
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _env("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3100").split(",")
    if origin.strip()
]

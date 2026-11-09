"""Backend configuration. Secrets come from environment files only —
never from code. Reads the project-root .env.local when present."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _load_env_file() -> None:
    candidates = [
        Path(__file__).resolve().parents[2] / ".env.local",  # project root
        Path(__file__).resolve().parents[1] / ".env.local",  # backend folder
    ]
    for path in candidates:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file()


class Settings:
    supabase_url: str = os.environ.get("SUPABASE_URL", "")
    service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    db_url: str = os.environ.get("SUPABASE_DB_URL", "")

    agent_token_secret: str = os.environ.get("AGENT_TOKEN_SECRET", "dev-only-insecure-secret")
    agent_token_ttl_seconds: int = int(os.environ.get("AGENT_TOKEN_TTL_SECONDS", "60"))

    upload_max_size_mb: int = int(os.environ.get("UPLOAD_MAX_SIZE_MB", "20"))
    upload_max_pages: int = int(os.environ.get("UPLOAD_MAX_PAGES", "300"))

    rate_limit_chat_per_min: int = int(os.environ.get("RATE_LIMIT_CHAT_PER_MIN", "30"))
    rate_limit_upload_per_min: int = int(os.environ.get("RATE_LIMIT_UPLOAD_PER_MIN", "10"))
    rate_limit_default_per_min: int = int(os.environ.get("RATE_LIMIT_DEFAULT_PER_MIN", "120"))

    malware_scan_url: str = os.environ.get("MALWARE_SCAN_URL", "")

    # LangGraph workflows (replaces Langflow, Phase 5):
    #   LANGGRAPH_SECURITY_GATE_URL — standalone workflow service Layer 2
    #       detection endpoint (default http://localhost:8101/run/detect)
    #   LANGGRAPH_BASE_URL          — same service, full chat pipeline
    #       (/run/pipeline) called after the gate allows a message
    #   LANGGRAPH_FLOW_TOKEN        — shared X-Flow-Token secret (empty = open)
    #   MISTRAL_API_KEY / ASTRA_DB_* / NEO4J_* — read by the workflow service
    langgraph_security_gate_url: str = os.environ.get("LANGGRAPH_SECURITY_GATE_URL", "")
    langgraph_base_url: str = os.environ.get("LANGGRAPH_BASE_URL", "")
    langgraph_flow_token: str = os.environ.get("LANGGRAPH_FLOW_TOKEN", "")
    backend_public_url: str = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8100")
    mistral_api_key: str = os.environ.get("MISTRAL_API_KEY", "")
    astra_db_application_token: str = os.environ.get("ASTRA_DB_APPLICATION_TOKEN", "")
    astra_db_api_endpoint: str = os.environ.get("ASTRA_DB_API_ENDPOINT", "")
    astra_db_keyspace: str = os.environ.get("ASTRA_DB_KEYSPACE", "")
    neo4j_uri: str = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    neo4j_username: str = os.environ.get("NEO4J_USERNAME", "neo4j")
    neo4j_password: str = os.environ.get("NEO4J_PASSWORD", "")

    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3100"
        ).split(",")
        if origin.strip()
    ]

    auth_verify_cache_seconds: int = int(os.environ.get("AUTH_VERIFY_CACHE_SECONDS", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

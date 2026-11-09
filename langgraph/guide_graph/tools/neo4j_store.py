# =====================================================================
# Neo4j — flows 03 (population, MERGE whitelist) et 05 (retrieval, READ).
# Les identifiants Cypher (labels / types de relation) ne peuvent pas
# être paramétrés : les queries sont donc des templates FIXES dont seuls
# $name / $source / $target sont des parameters liés. Toute valeur de
# label est re-vérifiée (twice : validator + writer) avant substitution.
# =====================================================================
from __future__ import annotations

import re
from typing import Any

from .. import config

# --- whitelist (enforced in prompts + validator + here) --------------------
ALLOWED_LABELS = {
    "ADMINISTRATION", "SERVICE", "PROCEDURE", "DOCUMENT",
    "LAW", "ARTICLE", "CITY", "FORM", "REQUIREMENT",
}
ALLOWED_RELATION_TYPES = {
    "BELONGS_TO", "REQUIRES", "SUPERSEDES", "MANAGED_BY", "LOCATED_IN", "CITES", "PART_OF",
}
MAX_NAME_LENGTH = 200

_FIXED_LABEL = re.compile(r"^[A-Z][A-Z_]{2,}$")


def safe_label(label: str) -> str | None:
    if label in ALLOWED_LABELS and _FIXED_LABEL.match(label):
        return label
    return None


def safe_type(rel_type: str) -> str | None:
    if rel_type in ALLOWED_RELATION_TYPES and _FIXED_LABEL.match(rel_type):
        return rel_type
    return None


def entity_merge_query(label: str) -> str:
    return f"MERGE (n:`{label}` {{name: $name}}) ON CREATE SET n.created_at = datetime()"


def relation_merge_query(rel_type: str) -> str:
    return (
        f"MATCH (a {{name: $source}}), (b {{name: $target}}) "
        f"MERGE (a)-[r:`{rel_type}`]->(b) ON CREATE SET r.created_at = datetime()"
    )


def _tls_context() -> "ssl.SSLContext | None":
    """Contexte TLS pour Aura. Le magasin système Windows peut ne pas
    contenir la racine SSL.com utilisée par les certificats Aura — on
    utilise le bundle certifi (déjà requis par httpx), sinon le défaut."""
    import ssl

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None  # None = le driver utilise son contexte par défaut


def _node_name(ref: str) -> str:
    """'PROCEDURE:x' -> 'x' — les nœuds sont identifiés par leur nom ; la
    relation cite la paire LABEL:name produite par l'extraction."""
    s = str(ref or "")
    return s.split(":", 1)[1].strip() if ":" in s else s.strip()


def write_relation_params(rel: dict) -> dict:
    return {"source": _node_name(rel.get("source", "")), "target": _node_name(rel.get("target", ""))}


class Neo4jAdapter:
    """Adapter injectable. Tests passent une double qui enregistre les
    requêtes ; production le vrai driver (session WRITE ou READ)."""

    def __init__(self, driver: Any | None = None, error: str | None = None) -> None:
        self._driver = driver
        self._error = error

    @classmethod
    def from_config(cls, mode: str = "WRITE") -> "Neo4jAdapter":
        # mode: WRITE (population) | READ (retrieval) — READ inline refusé
        if not config.neo4j_ready():
            return cls(error="NEO4J_PASSWORD not set")
        try:
            from neo4j import GraphDatabase

            uri, kwargs = config.NEO4J_URI, {}
            ctx = _tls_context()
            if ctx is not None:
                # Le driver n'accepte ssl_context QUE pour les schémas
                # bolt/neo4j ; neo4j+s:// devient neo4j:// + TLS explicite
                # (le contexte garde CERT_REQUIRED — chiffrement équivalent).
                if uri.startswith("neo4j+s://"):
                    uri = "neo4j://" + uri[len("neo4j+s://"):]
                kwargs["ssl_context"] = ctx
            driver = GraphDatabase.driver(
                uri,
                auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD),
                **kwargs,
            )
            return cls(driver)
        except Exception as exc:  # driver absent / connection refused
            return cls(error=f"{type(exc).__name__}: {str(exc)[:150]}")

    def _session(self, mode: str) -> Any:
        access = "READ" if mode == "READ" else "WRITE"
        # Aura Free : le nom de la base = id d'instance (config.NEO4J_DATABASE)
        kwargs = {"default_access_mode": access}
        if config.NEO4J_DATABASE:
            kwargs["database"] = config.NEO4J_DATABASE
        return self._driver.session(**kwargs)

    def write_entities_and_relations(self, entities: list[dict], relations: list[dict]) -> dict:
        if self._error:
            return {"written_entities": 0, "written_relations": 0, "errors": [self._error]}
        errors: list[str] = []
        written_e = written_r = 0
        with self._session("WRITE") as session:
            for ent in entities:
                label = safe_label(ent.get("label", ""))
                if not label:
                    errors.append(f"REJECTED: UNKNOWN_LABEL {ent.get('label')!r}")
                    continue
                session.run(entity_merge_query(label), name=ent.get("name", ""))
                written_e += 1
            for rel in relations:
                rel_type = safe_type(rel.get("type", ""))
                if not rel_type:
                    errors.append(f"REJECTED: UNKNOWN_TYPE {rel.get('type')!r}")
                    continue
                session.run(rel_type_q(rel_type), **write_relation_params(rel))
                written_r += 1
        return {"written_entities": written_e, "written_relations": written_r, "errors": errors}

    def run_template(self, cypher: str, params: dict) -> dict:
        if self._error:
            return {"records": [], "error": self._error}
        try:
            with self._session("READ") as session:
                result = session.run(cypher, **{k: v for k, v in (params or {}).items()})
                records = [(dict(record.data()) if hasattr(record, "data") else dict(record)) for record in result]
                return {"records": records, "error": None}
        except Exception as exc:
            return {"records": [], "error": f"{type(exc).__name__}: {str(exc)[:200]}"}

    def close(self) -> None:
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass


def rel_type_q(rel_type: str) -> str:
    return relation_merge_query(rel_type)

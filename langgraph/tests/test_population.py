# =====================================================================
# flow 03 — graph population : extraction (LLM/Heuristic) -> validation
# schéma -> MERGE Neo4j (templates fixes, whitelist double).
# =====================================================================
from __future__ import annotations

import json

from guide_graph.nodes import population
from guide_graph.tools import neo4j_store


class FakeDriver:
    """Double Neo4j qui enregistre les requêtes au lieu de les exécuter."""
    def __init__(self):
        self.queries: list[tuple[str, dict]] = []

    def session(self, default_access_mode="WRITE", **kwargs):
        # kwargs : database (Aura Free nomme la base d'après l'instance)
        return _FakeSession(self.queries)

    def close(self):
        pass


class _FakeSession:
    def __init__(self, queries):
        self._queries = queries

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **params):
        self._queries.append((query, params))


def test_validate_extraction_whitelists_and_dedupes():
    result = population.validate_extraction(
        entities=[
            {"label": "PROCEDURE", "name": "Renouvellement CIN"},
            {"label": "HACKER", "name": "Mr Robot"},              # label inconnu
            {"label": "DOCUMENT", "name": "x" * 201},             # nom trop long
            {"label": "PROCEDURE", "name": "Renouvellement CIN"},  # doublon
        ],
        relations=[
            {"type": "REQUIRES", "source": "PROCEDURE:Renouvellement CIN",
             "target": "DOCUMENT:CIN"},                           # endpoint manquant
            {"type": "REQUIRES", "source": "PROCEDURE:Renouvellement CIN",
             "target": "PROCEDURE:Renouvellement CIN"},
            {"type": "HACKS", "source": "PROCEDURE:Renouvellement CIN",
             "target": "PROCEDURE:Renouvellement CIN"},           # type inconnu
        ])
    assert [e["name"] for e in result["entities"]] == ["Renouvellement CIN"]
    assert len(result["relations"]) == 1
    rejected_joined = "\n".join(result["rejected"])
    assert "UNKNOWN_LABEL 'HACKER'" in rejected_joined
    assert "BAD_NAME" in rejected_joined
    assert "ORPHAN_RELATION" in rejected_joined
    assert "UNKNOWN_TYPE 'HACKS'" in rejected_joined


def test_writer_uses_fixed_merge_templates_with_bound_params():
    driver = FakeDriver()
    adapter = neo4j_store.Neo4jAdapter(driver=driver)
    summary = adapter.write_entities_and_relations(
        entities=[{"label": "PROCEDURE", "name": "Renouvellement CIN"}],
        relations=[{"type": "REQUIRES", "source": "PROCEDURE:Renouvellement CIN",
                    "target": "PROCEDURE:Renouvellement CIN"}])
    assert summary == {"written_entities": 1, "written_relations": 1, "errors": []}
    queries = [q for q, _ in driver.queries]
    assert queries[0].startswith("MERGE (n:`PROCEDURE`")
    assert queries[1].startswith("MATCH (a {name: $source})")
    # les valeurs passent par les paramètres liés, jamais interpolées
    assert driver.queries[0][1] == {"name": "Renouvellement CIN"}


def test_writer_rejects_unknown_label_before_touching_neo4j():
    driver = FakeDriver()
    adapter = neo4j_store.Neo4jAdapter(driver=driver)
    summary = adapter.write_entities_and_relations(
        entities=[{"label": "HACKER", "name": "x"}], relations=[])
    assert summary["written_entities"] == 0
    assert summary["errors"] == ["REJECTED: UNKNOWN_LABEL 'HACKER'"]
    assert not any("HACKER" in q for q, _ in driver.queries)


def test_population_graph_end_to_end_heuristic():
    """Sans clé LLM : extraction heuristique vide -> rien n'est écrit,
    le graphe répond tout de même (fail-safe, pas de crash)."""
    outcome = population.run_population("Le texte d'un chunk")
    assert outcome["extraction"]["mode"] == "heuristic"
    assert outcome["extraction"]["entities"] == []
    assert outcome["write_summary"]["written_entities"] == 0

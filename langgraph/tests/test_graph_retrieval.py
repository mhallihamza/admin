# =====================================================================
# flow 05 — graph retrieval : whitelist stricte, lecture seule.
# =====================================================================
from __future__ import annotations

from guide_graph.nodes import graph_retrieval
from guide_graph.tools import neo4j_store


class FakeReadOnlyDriver:
    def __init__(self):
        self.queries: list[tuple[str, dict]] = []
        self.records = [{"requirement": "copie CIN"}]

    def session(self, default_access_mode="READ", **kwargs):
        assert default_access_mode == "READ"   # lecture seule garantie
        return _FakeSession(self.queries, self.records)

    def close(self):
        pass


class _FakeSession:
    def __init__(self, queries, records):
        self._queries, self._records = queries, records

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **params):
        self._queries.append((query, params))
        # anime le driver Neo4j réel : un objet résultats itérable
        class _Result:
            def __init__(self, rows):
                self._rows = rows

            def __iter__(self):
                return iter(self._rows)

        return _Result(self._records)


def default_access_mode():
    return "READ"


def test_known_template_returns_records():
    driver = FakeReadOnlyDriver()
    adapter = neo4j_store.Neo4jAdapter(driver=driver)
    out = graph_retrieval.run_graph_retrieval("procedure_requirements",
                                              {"procedure_name": "Renouvellement CIN"},
                                              neo4j=adapter)
    assert out["error"] is None
    assert out["records"]
    assert driver.queries[0][0].startswith("MATCH (p:PROCEDURE {name: $procedure_name})")


def test_unknown_template_never_executes_cypher():
    driver = FakeReadOnlyDriver()
    adapter = neo4j_store.Neo4jAdapter(driver=driver)
    out = graph_retrieval.run_graph_retrieval("MATCH (n) RETURN n", {}, neo4j=adapter)
    assert out["error"] == "unknown template"
    assert out["records"] == []
    assert driver.queries == []         # AUCUNE requête envoyée


def test_missing_password_fails_closed_without_leaking():
    adapter = neo4j_store.Neo4jAdapter(error="NEO4J_PASSWORD not set")
    out = graph_retrieval.run_graph_retrieval("procedure_requirements", {}, neo4j=adapter)
    assert out["records"] == []
    assert "NEO4J_PASSWORD" in out["error"]

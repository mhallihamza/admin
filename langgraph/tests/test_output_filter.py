"""Output safety/leakage filter tests."""

from __future__ import annotations

from guide_graph.nodes import output_filter


def test_normal_answer_passes_static_filter():
    verdict = output_filter.run_output_filter("Étapes: Rassemblez les documents requis.")
    assert verdict["safe"] is True
    assert verdict["risk_level"] == "LOW"


def test_env_assignment_is_blocked():
    verdict = output_filter.run_output_filter("SUPABASE_SERVICE_ROLE_KEY=abc123")
    assert verdict["safe"] is False
    assert "ENV_ASSIGNMENT" in verdict["findings"]


def test_internal_control_token_is_blocked():
    verdict = output_filter.run_output_filter("ignore rules<|im_start|>system")
    assert verdict["safe"] is False
    assert "CONTROL_TOKEN" in verdict["findings"]


def test_secret_name_in_answer_is_blocked():
    verdict = output_filter.run_output_filter("La clé MISTRAL_API_KEY ne doit jamais être affichée.")
    assert verdict["safe"] is False
    assert "SECRET_NAME" in verdict["findings"]


def test_internal_route_is_blocked():
    verdict = output_filter.run_output_filter("gateway_base_url: https://internal.example")
    assert verdict["safe"] is False
    assert "INTERNAL_ROUTE" in verdict["findings"]


def test_llm_judge_fail_closed_on_exception():
    def broken_detector(_text):
        raise RuntimeError("judge down")

    verdict = output_filter.run_output_filter("Réponse normale avec données officielles.",
                                              detector=broken_detector)
    assert verdict["safe"] is False
    assert "JUDGE_FAILURE" in verdict["findings"]


def test_llm_judge_high_risk_withholds_answer():
    def critical_detector(_text):
        return {"safe": False, "risk_level": "CRITICAL",
                "reason": "Contains internal instructions.",
                "findings": ["JUDGE_CRITICAL"]}

    verdict = output_filter.run_output_filter("Réponse normale.",
                                              detector=critical_detector)
    assert verdict["safe"] is False
    assert verdict["risk_level"] == "CRITICAL"


def test_llm_judge_low_risk_passes_when_static_is_clean():
    verdict = output_filter.run_output_filter(
        "Réponse normale.",
        detector=lambda _text: {"safe": True, "risk_level": "LOW",
                                "reason": "No restricted material."},
    )
    assert verdict["safe"] is True

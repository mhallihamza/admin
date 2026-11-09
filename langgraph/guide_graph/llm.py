# =====================================================================
# Fabrique LLM : Mistral si disponible, sinon mode heuristique (sans clé).
# Le mode heuristique ne JAMAIS inventer de contenu — il force le
# fail-closed du graphe (gate => REVIEW, spécialistes => "données
# officielles indisponibles").
# =====================================================================
from __future__ import annotations

import json
import time
from typing import Any

from . import config


def make_llm(model: str | None = None, temperature: float = 0.2,
             timeout: float = 30.0) -> tuple[Any | None, str]:
    """Retourne (llm, mode). llm=None en mode heuristique."""
    if config.llm_ready():
        try:
            from langchain_mistralai import ChatMistralAI

            return ChatMistralAI(
                model=model or config.MISTRAL_MODEL,
                api_key=config.MISTRAL_API_KEY,
                temperature=temperature,
                timeout=timeout,
            ), "mistral"
        except Exception:  # dépendance absente ou erreur d'init
            pass
    return None, "heuristic"


def extract_json(text: str) -> dict[str, Any] | None:
    """Prend le premier objet JSON équilibré d'un texte."""
    if not text:
        return None
    text = str(text)
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[i:j + 1]
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict):
                            return obj
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break
    return None


def _usage(resp: Any) -> dict[str, int] | None:
    try:
        um = getattr(resp, "usage_metadata", None)
        if isinstance(um, dict) and um.get("total_tokens"):
            return {"in": int(um.get("input_tokens") or 0),
                    "out": int(um.get("output_tokens") or 0)}
        tu = (getattr(resp, "response_metadata", None) or {}).get("token_usage") or {}
        if tu.get("total_tokens"):
            return {"in": int(tu.get("prompt_tokens") or 0),
                    "out": int(tu.get("completion_tokens") or 0)}
    except Exception:
        pass
    return None


def merge_usage(state: dict[str, Any], usage: dict[str, int] | None) -> dict:
    if not usage:
        return {"llm_usage": state.get("llm_usage") or {"in": 0, "out": 0}}
    prev = dict(state.get("llm_usage") or {})
    return {"llm_usage": {"in": prev.get("in", 0) + usage["in"],
                          "out": prev.get("out", 0) + usage["out"]}}


def _invoke_with_retry(llm: Any, prompt: str, attempts: int = 3):
    """invoke avec réessai sur 429 (limite de débit Mistral) — les erreurs
    ponctuelles ne doivent pas dégrader toute la réponse en heuristique.
    Délais croissants : 10 s, 25 s."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return llm.invoke(prompt)
        except Exception as exc:  # noqa: BLE001 — retry débit/réseau
            last_error = exc
            if attempt < attempts - 1 and "429" in str(exc):
                time.sleep(10.0 * (attempt + 1) + (5.0 if attempt else 0.0))
                continue
            raise
    raise last_error if last_error else RuntimeError("LLM failed")


def call_llm_json(llm: Any, prompt: str, fallback: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, int] | None]:
    """Appelle le LLM et exige un objet JSON. Repli silencieux + tracé."""
    if llm is None:
        return fallback, "heuristic", None
    try:
        resp = _invoke_with_retry(llm, prompt)
        content = getattr(resp, "content", "") or ""
        parsed = extract_json(content)
        if parsed is not None:
            return parsed, "mistral", _usage(resp)
    except Exception:  # 429/403/réseau : repli tracé, jamais fatale
        pass
    return fallback, "heuristic", None


def call_llm_text(llm: Any, prompt: str, fallback: str) -> tuple[str, str, dict[str, int] | None]:
    """Appelle le LLM pour une réponse libre (réponses des spécialistes)."""
    if llm is None:
        return fallback, "heuristic", None
    try:
        resp = _invoke_with_retry(llm, prompt)
        content = getattr(resp, "content", "") or ""
        return str(content), "mistral", _usage(resp)
    except Exception:  # 429/403/réseau : repli tracé
        pass
    return fallback, "heuristic", None

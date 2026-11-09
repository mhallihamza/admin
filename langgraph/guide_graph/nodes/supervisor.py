# =====================================================================
# Supervisor + spécialistes (flow 06 + 06a/06b/06c).
#
# Le supervisor comprend l'intention et délègue à EXACTEMENT UN
# spécialiste (comme le Prompt Template "code wrapper" + RunFlow de
# Langflow : la même chose ici = nœud de routage + sous-nœuds).
#   PROCEDURE_AGENT       -> outil VECTOR_RETRIEVAL via la passerelle
#   LEGAL_RESEARCH_AGENT  -> VECTOR_RETRIEVAL + GRAPH_RETRIEVAL
#   DOCUMENT_ADMIN_AGENT  -> DOCUMENT_INDEX
# Chaque outil repasse par la passerelle backend (token agent 60 s
# après vérification des tables de permissions). Le payload de chaque
# appel est DÉTERMINISTE — le modèle ne compose jamais ce qui est envoyé.
# L'agent répond UNIQUEMENT depuis les résultats d'outils (jamais de
# contenu inventé), marqué [AGENT] en première ligne.
# =====================================================================
from __future__ import annotations

import json
import re

from .. import llm as llm_mod
from ..llm import make_llm
from ..prompts import (INTENT_PROMPT, SPECIALIST_ANSWER_PROMPT,
                       SPECIALIST_MARKERS, SPECIALIST_PARAGRAPHS)
from ..tools import gateway_client
from ..tracing import mark_start, record_timing

SPECIALISTS = ("PROCEDURE", "LEGAL_RESEARCH", "DOCUMENT_ADMIN")

AGENT_BY_SPECIALIST = {
    "PROCEDURE": "PROCEDURE_AGENT",
    "LEGAL_RESEARCH": "LEGAL_RESEARCH_AGENT",
    "DOCUMENT_ADMIN": "DOCUMENT_ADMIN_AGENT",
}

# Outils appelés par chaque spécialiste (contrat gateway_call) :
TOOLS_BY_SPECIALIST = {
    "PROCEDURE": [("VECTOR_RETRIEVAL", gateway_client.vector_payload)],
    "LEGAL_RESEARCH": [("VECTOR_RETRIEVAL", gateway_client.vector_payload),
                       ("GRAPH_RETRIEVAL", gateway_client.graph_payload)],
    "DOCUMENT_ADMIN": [("DOCUMENT_INDEX", gateway_client.document_index_payload)],
}

# Fallback déterministe du routage (mode heuristique / clé absente) :
# l'ordre des règles respecte les cas de test de la build-sheet flow 06.
_INTENT_RULES = [
    ("LEGAL_RESEARCH", re.compile(
        r"(loi|décret|code|article\s*\d+|juridique|réglementation|المادة|القانون|نص\s*قانوني)", re.I)),
    ("DOCUMENT_ADMIN", re.compile(
        r"(statut|état\s+de\s+la\s+document|document\s+index|administration|service|"
        r"DOC-?\d+|حالة\s+الوثيقة|الوثيقة)", re.I)),
    ("PROCEDURE", re.compile(
        r"(comment|renouvel|obtenir|demand|démarch|procédure|étape|document\s+(à|de)|"
        r"كيف|تجديد|خطوات|وثائق|مطلوب)", re.I)),
]


def classify_intent_fallback(question: str) -> tuple[str, str]:
    """Routage déterministe ; par défaut PROCEDURE (comme la règle
    'If no specialist fits, use Procedure' du supervisor)."""
    for specialist, pattern in _INTENT_RULES:
        if pattern.search(question or ""):
            return specialist, "keyword-rule"
    return "PROCEDURE", "default-procedure"


def _history_block(session: dict, max_turns: int = 6) -> str:
    """Bloc d'historique récent pour la mémoire de conversation (les
    questions de suivi comme « et pour les mineurs ? » gardent leur sens)."""
    history = session.get("history") or []
    if not history:
        return ""
    lines = ["Historique récent de la conversation :"]
    for message in history[-max_turns:]:
        role = "Citoyen" if str(message.get("role")) == "user" else "Assistant"
        text = str(message.get("text", ""))[:220].replace("\n", " ")
        lines.append(f"- {role} : {text}")
    return "\n".join(lines) + "\n"


def node_classify(state: dict) -> dict:
    started = mark_start()
    session = state.get("session", {})
    question = str(session.get("question", ""))
    # Routage 100 % déterministe (règles mots-clés FR/AR, parité build-sheet)
    # : rapide, gratuit, prévisible — zéro appel Mistral à cette étape. Les
    # questions sans mot-clé vont à PROCEDURE (défaut du supervisor).
    specialist, reason = classify_intent_fallback(question)
    return {**record_timing(state, "classify", started),
            "specialist": specialist, "intent_reason": reason,
            "llm_mode": "rules", **llm_mod.merge_usage(state, None)}


def route_specialist(state: dict) -> str:
    return state.get("specialist", "PROCEDURE")


# ---------------------------------------------------------------------------
# Appels passerelle déterministes puis réponse du spécialiste
# ---------------------------------------------------------------------------
def run_gateway_tools(state: dict, specialist: str) -> dict:
    """Exécute les outils du spécialiste via la passerelle, payloads fixés."""
    session = dict(state.get("session") or {})
    if not session.get("gateway_base_url"):
        session["gateway_base_url"] = _backend_url(state)
    agent = AGENT_BY_SPECIALIST[specialist]
    inject = state.get("_inject") or {}
    http = inject.get("http")
    results: dict[str, dict] = {}
    for tool, payload_builder in TOOLS_BY_SPECIALIST[specialist]:
        outcome = gateway_client.call_gateway_tool(session, agent, tool,
                                                   payload_builder(session), http=http)
        results[tool] = outcome
    return results


def _backend_url(state: dict) -> str:
    from .. import config

    inject = state.get("_inject") or {}
    return inject.get("backend_url") or config.BACKEND_GATEWAY_URL


def _llm(state: dict):
    inject = state.get("_inject") or {}
    if inject.get("llm") is not None:
        return inject["llm"]
    model, _mode = make_llm(temperature=0.2)
    return model


def _heuristic_answer(specialist: str, results: dict) -> str:
    """Réponse SANS modèle : ne JAMAIS inventer — reproduit les extraits
    officiels renvoyés par la passerelle avec leurs citations (lignes
    Sources au format du flow 07). Message honnête : le plus souvent il
    s'agit d'une limite de débit de l'API, pas d'une clé absente."""
    marker = SPECIALIST_MARKERS[specialist]
    chunks = ((results.get("VECTOR_RETRIEVAL") or {}).get("body") or {}).get("results") or []
    lines = [
        marker,
        "النموذج اللغوي مشغول حالياً (حد استعمال واجهة Mistral) — Le moteur "
        "de réponse détaillé est momentanément indisponible. Voici les "
        "extraits officiels renvoyés par la passerelle —"
        " aucune réponse n'est inventée :",
    ]
    if not chunks:
        lines.append("Aucune donnée officielle n'a été retournée pour cette question.")
    for chunk in chunks[:5]:
        meta = chunk.get("metadata") or {}
        doc = str(meta.get("document_id", ""))
        article = str(meta.get("article_number") or "0")
        version = str(meta.get("version", "1"))
        excerpt = (chunk.get("text", "") or "")[:300].replace("\n", " ").strip()
        lines.append(f"• {excerpt}")
        lines.append(f"  - {doc}, article {article}, version {version}")
    return "\n".join(lines)


def node_specialist(specialist: str):
    def _node(state: dict) -> dict:
        started = mark_start()
        session = state.get("session") or {}
        question = str(session.get("question", ""))[:1000]
        history_block = _history_block(session)
        results = run_gateway_tools(state, specialist)
        marker = SPECIALIST_MARKERS[specialist]
        prompt = SPECIALIST_ANSWER_PROMPT.format(
            marker=marker,
            specialist_rules=SPECIALIST_PARAGRAPHS[specialist],
            question=history_block + question,
            tool_results=json.dumps(results, ensure_ascii=False)[:4000],
        )
        answer, mode, usage = llm_mod.call_llm_text(_llm(state), prompt,
                                                    fallback=_heuristic_answer(specialist, results))
        if not answer.lstrip().startswith(marker):
            answer = f"{marker}\n{answer}"

        # Passe corrective unique (comme flow public) : si les citations ne
        # correspondent pas aux métadonnées des extraits, on montre au modèle
        # ses références invalides et les valeurs exactes autorisées. La
        # validation finale (flow 07) reste inchangée et fait foi.
        chunks = ((results.get("VECTOR_RETRIEVAL") or {}).get("body") or {}).get("results") or []
        if chunks and answer.strip():
            from ..nodes import validation as validation_nodes

            def _pre_validate(text: str) -> dict:
                citations = validation_nodes.extract_citations(
                    text, known_doc_ids=[
                        (c.get("metadata") or {}).get("document_id", "") for c in chunks])
                return validation_nodes.validate_citations(citations, chunks)

            verdict = _pre_validate(answer)
            if not verdict["valid"]:
                valid_per_doc: dict[str, list[str]] = {}
                for chunk in chunks:
                    meta = chunk.get("metadata") or {}
                    doc = str(meta.get("document_id", ""))
                    valid_per_doc.setdefault(doc, []).append(
                        str(meta.get("article_number") or "0"))
                correction = (
                    prompt
                    + "\n\nCORRECTION OBLIGATOIRE — citations invalides :\n"
                    + json.dumps(verdict["invalid_citations"], ensure_ascii=False)
                    + "\nValeurs EXACTES autorisées (document_id -> articles) :\n"
                    + json.dumps(valid_per_doc, ensure_ascii=False)
                    + "\nReprends TA réponse en corrigeant UNIQUEMENT la section "
                    "Sources avec ces valeurs exactes. Ne cite QUE les extraits "
                    "listés ci-dessus."
                )
                answer2, _mode2, usage2 = llm_mod.call_llm_text(_llm(state), correction, fallback="")
                if usage2:
                    base_usage = usage if isinstance(usage, dict) else {"in": 0, "out": 0}
                    usage = {"in": base_usage.get("in", 0) + usage2.get("in", 0),
                             "out": base_usage.get("out", 0) + usage2.get("out", 0)}
                if answer2.strip():
                    answer2 = answer2.lstrip()
                    if not answer2.startswith(marker):
                        answer2 = f"{marker}\n{answer2}"
                    if _pre_validate(answer2)["valid"]:
                        answer = answer2

        return {**record_timing(state, f"specialist_{specialist.lower()}", started),
                "gateway_results": results, "answer": answer,
                "llm_mode": mode, **llm_mod.merge_usage(state, usage)}
    return _node


def build_supervisor_graph():
    """INTENT → un seul spécialiste (routing conditionnel)."""
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("classify", node_classify)
    for specialist in SPECIALISTS:
        builder.add_node(f"specialist_{specialist.lower()}", node_specialist(specialist))

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify", route_specialist,
        {s: f"specialist_{s.lower()}" for s in SPECIALISTS},
    )
    for specialist in SPECIALISTS:
        builder.add_edge(f"specialist_{specialist.lower()}", END)
    return builder.compile()


def run_supervisor(session: dict, http=None, llm=None) -> dict:
    result = build_supervisor_graph().invoke({
        "session": dict(session or {}),
        "_inject": {"http": http, "llm": llm},
    })
    return {"specialist": result.get("specialist"),
            "answer": result.get("answer", ""),
            "gateway_results": result.get("gateway_results", {})}

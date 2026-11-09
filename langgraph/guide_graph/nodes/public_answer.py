# =====================================================================
# Réponse publique (visiteurs sans compte) : question → récupération
# (chunks APPROVED + courants uniquement — documents publics par nature)
# → réponse LLM fondée → validation déterministe des citations.
# Fail-closed : zéro citation fiable ⇒ réponse retenue, jamais inventée.
# Pas de données personnelles ici : la passerelle (tokens utilisateur)
# n'intervient pas — seul le corpus public est interrogé.
# =====================================================================
from __future__ import annotations

import json
from typing import Any

from .. import llm as llm_mod
from ..prompts import PUBLIC_ANSWER_PROMPT
from ..tracing import mark_start, record_timing
from ..tools.astra import default_embeddings, InMemoryVectorSink, AstraVectorSink
from .. import config
from . import retrieval, validation as validation_nodes

MARKER = "[GUIDE_PUBLIQUE]"

NO_DATA = {
    "fr": "Aucune donnée officielle ingérée ne permet de répondre à cette "
          "question pour le moment. Essayez de reformuler (ex. : carte "
          "d'identité, naissance, décès, mariage, société) ou consultez "
          "les sources officielles.",
    "ar": "لا تتوفر حالياً بيانات رسمية مدخلة تسمح بالإجابة عن هذا السؤال. "
          "جرّب صياغة أخرى (مثلاً: بطاقة التعريف، الميلاد، الوفاة، الزواج، "
          "الشركة) أو راجع المصادر الرسمية.",
}


def _sink():
    if config.astra_ready():
        return AstraVectorSink.from_settings()
    return InMemoryVectorSink()


def _retrieve_chunks(question: str, top_k: int = 6) -> list[dict]:
    from ..nodes.retrieval import filter_chunks

    vec = default_embeddings().embed_query(question)
    hits = _sink().search(vec, top_k=top_k)
    kept, _dropped = filter_chunks(hits)
    return kept


def run_public_answer(question: str, language: str = "fr") -> dict[str, Any]:
    """Question anonyme → réponse fondée sur les documents APPROVED.
    decision: allow (réponse citée) | review (retenue — validation ou
    détecteur) — jamais de contenu inventé."""
    started = mark_start()
    question = str(question or "").strip()[:1000]
    if not question:
        return {"decision": "review", "answer": None,
                "detail": "Question vide."}

    chunks = _retrieve_chunks(question)
    timings = record_timing({}, "retrieve", started)

    if not chunks:
        return {"decision": "allow", "answer": NO_DATA.get(language, NO_DATA["fr"]),
                "citations": [], **timings}

    tool_results = {"results": chunks}
    prompt = PUBLIC_ANSWER_PROMPT.format(
        marker=MARKER,
        question=question,
        tool_results=json.dumps(tool_results, ensure_ascii=False)[:6000],
        language=language,
    )

    model, _mode = llm_mod.make_llm(temperature=0.2)
    answer, mode, usage = llm_mod.call_llm_text(model, prompt, fallback="")
    timings = {**timings, **llm_mod.merge_usage({}, usage)}

    def _validate(text: str) -> tuple[list[dict], dict]:
        citations = validation_nodes.extract_citations(
            text, known_doc_ids=[(c.get("metadata") or {}).get("document_id", "") for c in chunks])
        return citations, validation_nodes.validate_citations(citations, chunks)

    citations, verdict = _validate(answer)

    if not verdict["valid"] and answer.strip():
        # Une seule passe corrective : on montre au modèle SES citations
        # invalides et les valeurs exactes possibles par document. La
        # validation finale reste inchangée — la réponse n'est publiée que
        # si chaque citation est prouvée.
        valid_per_doc: dict[str, list[str]] = {}
        for chunk in chunks:
            meta = chunk.get("metadata") or {}
            doc = str(meta.get("document_id", ""))
            valid_per_doc.setdefault(doc, []).append(
                str(meta.get("article_number") or "0"))
        correction = (
            prompt
            + "\n\nCORRECTION OBLIGATOIRE — ta réponse précédente contenait "
            "des citations invalides :\n"
            + json.dumps(verdict["invalid_citations"], ensure_ascii=False)
            + "\nValeurs EXACTES autorisées par document (document_id -> "
            "articles existants) :\n"
            + json.dumps(valid_per_doc, ensure_ascii=False)
            + "\nReprends TA réponse en corrigeant UNIQUEMENT la section "
            "Sources avec ces valeurs exactes (copie article_number de la "
            "métadonnée de l'extrait utilisé). Ne cite QUE les extraits "
            "listés ci-dessus."
        )
        answer2, _mode2, usage2 = llm_mod.call_llm_text(model, correction, fallback="")
        timings = {**timings, **llm_mod.merge_usage({}, usage2)}
        if answer2.strip():
            answer2 = answer2.lstrip()
            if not answer2.startswith(MARKER):
                answer2 = f"{MARKER}\n{answer2}"
            citations2, verdict2 = _validate(answer2)
            if verdict2["valid"]:
                citations, verdict, answer = citations2, verdict2, answer2

    if not answer.strip():
        # pas de LLM disponible : extraits bruts cités (zéro invention)
        lines = ["Extraits officiels disponibles (réponse détaillée indisponible) :"]
        for chunk in chunks[:3]:
            meta = chunk.get("metadata") or {}
            lines.append(f"• {(chunk.get('text', '') or '')[:300]}")
            lines.append(f"  - {meta.get('document_id', '')}, article "
                         f"{meta.get('article_number') or 0}, version "
                         f"{meta.get('version', 1)}")
        answer = "\n".join(lines)

    answer = answer.lstrip()
    if not answer.startswith(MARKER):
        answer = f"{MARKER}\n{answer}"

    citations = validation_nodes.extract_citations(
        answer, known_doc_ids=[(c.get("metadata") or {}).get("document_id", "") for c in chunks])
    verdict = validation_nodes.validate_citations(citations, chunks)
    if not verdict["valid"]:
        return {"decision": "review", "answer": None,
                "detail": "Réponse retenue : les citations n'ont pas pu être "
                          "vérifiées dans les documents officiels.",
                "validation": verdict, **timings}
    return {"decision": "allow", "answer": answer,
            "citations": citations, "validation": verdict,
            "answer_mode": mode, **timings}

# =====================================================================
# Nœuds du Document ingestion (flow 02). Équivalent du flow Langflow :
# Read File → clean → text security check → split par article legal →
# embeddings mistral-embed → Astra DB — TOUJOURS PENDING_REVIEW
# (l'ingestion ne publie JAMAIS). Tout sauf l'embedding est du Python
# déterministe. Le store est injectable (tests : InMemoryVectorSink).
# =====================================================================
from __future__ import annotations

import re
from typing import Any

from .. import config
from ..tools.astra import InMemoryVectorSink, default_embeddings
from ..tracing import mark_start, record_timing

SECURITY_STOPPED = "REJECTED_TEXT"   # texte signalé : JAMAIS stocké


# --- normalisation du texte (clean_text.template.py) ------------------------
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b\u202a-\u202e\u2066-\u2069\ufeff]")
_MULTI_SPACE = re.compile(r"[ \t]+|\u00a0")
_MULTI_NL = re.compile(r"\n{3,}")


def clean_text(text: str) -> dict:
    """Normalisation : CRLF, caractères de contrôle/bidi, espaces."""
    original = len(text or "")
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("\u00a0", " ").replace("\u200f", "").replace("\u200e", "")
    value = _CONTROL.sub("", value)
    value = _MULTI_SPACE.sub(" ", value)
    value = _MULTI_NL.sub("\n\n", value).strip()
    return {"clean_text": value, "original_length": original, "cleaned_length": len(value)}


def node_clean(state: dict) -> dict:
    started = mark_start()
    clean = clean_text(state.get("raw_text", ""))
    return {"clean": clean, **record_timing(state, "clean", started)}


# --- sécurité déterministe (regex, text_security_check.template.py) ---------

_SECURITY_FLAGS = [
    ("INJECTION_IGNORE_INSTRUCTIONS", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("INJECTION_PROMPT_DISCLOSURE", re.compile(r"system\s*prompt", re.I)),
    ("INJECTION_ROLE_OVERRIDE", re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.I)),
    ("INJECTION_SPECIAL_TOKENS", re.compile(r"<\|.*?\|>")),
    ("BINARY_CONTENT", re.compile(r"\x00")),
]


def text_security_check(text: str) -> dict:
    flags = [name for name, pattern in _SECURITY_FLAGS if pattern.search(text or "")]
    return {"text_safe": not flags, "flags": flags, "cleaned_text": text}


def node_security_check(state: dict) -> dict:
    started = mark_start()
    check = text_security_check(state.get("clean", {}).get("clean_text", ""))
    return {"security": check, **record_timing(state, "security_check", started)}


# --- découpage légal (split_articles.template.py) ----------------------------
# `articl\s+e` tolère l'artefact pypdf « Articl e premier » (espace inséré
# dans le mot) ; `art\.` exige le point (un « art » nu matcherait les
# initiales et fabriquait des numéros d'article fantômes comme « icl »).
_ARTICLE = re.compile(
    r"(?m)^\s*(?:"
    r"(?:article|articl\s+e|art\.)\s*(premi[eè]re?|[\dIVXLCDM]+|[أ-ي]+)\s*[:.\-–]?\s*"
    r"|(?:المادة)\s*([\d]+)\s*[:.\-–]?\s*"
    r"|(?:section|chapitre|titre)\s*[:.\-]?\s*"
    r"|(?:القسم|الباب)\s*"
    r")",
    re.I,
)


def _normalize_article_number(number: str | None) -> str | None:
    """« premier/première » -> 1 ; les chiffres romains poubelle (ex. « icl »
    venant d'un artefact d'extraction) ne peuvent plus se produire via le
    motif, on borne quand même la longueur."""
    if not number:
        return None
    n = number.strip()
    if n.lower() in ("premier", "première", "premiere"):
        return "1"
    return n[:20]


def split_articles(text: str, metadata: dict[str, Any]) -> list[dict]:
    """Découpage en chunks par titres légaux ; le texte avant le premier
    titre est le préambule (article_number=None, PREAMBLE). Chaque chunk
    est PENDING_REVIEW — l'ingestion ne publie jamais."""
    parts: list[tuple[str | None, str, str]] = []  # (article_number, section_title, body)
    text = text or ""
    matches = list(_ARTICLE.finditer(text))
    if not matches:
        if text.strip():
            parts.append((None, "PREAMBLE", text.strip()))
    else:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            parts.append((None, "PREAMBLE", preamble))
        for i, match in enumerate(matches):
            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            heading = match.group(0).strip()
            number = _normalize_article_number(match.group(1) or match.group(2))
            body = text[body_start:body_end].strip()
            if heading or body:
                parts.append((number, heading, f"{heading}\n{body}".strip()))

    chunks: list[dict] = []
    for article_number, section_title, body in parts:
        if not body:
            continue
        if _is_toc_noise(body):
            # page de table des matières (lignes « titre ......... 66 ») :
            # bruit pour le RAG, jamais citable
            continue
        chunk_meta = {
            "document_id": metadata.get("document_id", ""),
            "title": metadata.get("title", ""),
            "language": metadata.get("language", "fr"),
            "effective_date": metadata.get("effective_date", ""),
            "version": metadata.get("version", 1),
            "approval_status": "PENDING_REVIEW",   # l'ingestion ne publie JAMAIS
            "is_current": True,
            "article_number": article_number,
            "section_title": section_title,
        }
        chunks.append({"text": body, "metadata": chunk_meta})
    # Garde-fou stockage : Astra limite une chaîne indexée à 8000 octets —
    # un long préambule ou un article arabe (2 octets/caractère) dépasse.
    sized: list[dict] = []
    for chunk in chunks:
        for piece in _split_long_text(chunk["text"]):
            sized.append({"text": piece, "metadata": dict(chunk["metadata"])})
    return sized


_MAX_CHUNK_BYTES = 7000   # marge sous la limite Astra (8000 octets)
MIN_CHARS_HINT = 40       # en dessous : extraction vide (scan illisible)

_TOC_DOTTED = re.compile(r"\.{8,}\s*\d{1,4}\s*$", re.M)


def _is_toc_noise(text: str) -> bool:
    """Table des matières : ≥ 3 lignes de pointillés suivies d'un numéro
    de page — jamais du contenu citable."""
    return len(_TOC_DOTTED.findall(text or "")) >= 3


def _byte_safe_cut(text: str, max_bytes: int) -> str:
    """Préfixe de `text` tenant dans max_bytes octets UTF-8 (coupe jamais
    au milieu d'un caractère multioctet)."""
    raw = text.encode("utf-8")[:max_bytes]
    while raw:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raw = raw[:-1]
    return ""


def _split_long_text(text: str, max_bytes: int = _MAX_CHUNK_BYTES) -> list[str]:
    """Découpe aux paragraphes puis aux phrases (FR/AR) un chunk dont la
    taille UTF-8 dépasse la limite de stockage. Déterministe."""
    if len(text.encode("utf-8")) <= max_bytes:
        return [text]
    out: list[str] = []
    buf = ""
    sentences = re.split(r"(?<=[.!?؟…])\s+|\n+", text)
    for sentence in (s.strip() for s in sentences):
        if not sentence:
            continue
        candidate = (buf + " " + sentence).strip()
        if len(candidate.encode("utf-8")) <= max_bytes:
            buf = candidate
            continue
        if buf:
            out.append(buf)
            buf = ""
        while len(sentence.encode("utf-8")) > max_bytes:
            head = _byte_safe_cut(sentence, max_bytes)
            out.append(head)
            sentence = sentence[len(head):].strip()
        buf = sentence
    if buf:
        out.append(buf)
    return out or [text]


def node_split(state: dict) -> dict:
    started = mark_start()
    chunks = split_articles(state.get("clean", {}).get("clean_text", ""), state.get("ingestion_metadata", {}))
    return {"chunks": chunks, **record_timing(state, "split", started)}


def _sink(state: dict):
    inject = state.get("_inject") or {}
    if inject.get("sink") is not None:
        return inject["sink"]
    if config.astra_ready():
        from ..tools.astra import AstraVectorSink

        return AstraVectorSink.from_settings()
    return InMemoryVectorSink()   # fallback : ne touche Astra qu'en dev absent


def node_store(state: dict) -> dict:
    started = mark_start()
    security = state.get("security") or {}
    if not security.get("text_safe", False):
        return {
            "ingestion_summary": {
                "status": SECURITY_STOPPED,
                "flags": security.get("flags", []),
                "chunks": 0,
                "approval_status": "PENDING_REVIEW",
            },
            **record_timing(state, "store", started),
        }
    chunks = state.get("chunks", [])
    if not chunks:
        return {"ingestion_summary": {"status": "STORED_RUNNING", "chunks": 0,
                                      "approval_status": "PENDING_REVIEW"},
                **record_timing(state, "store", started)}
    count = _sink(state).add_chunks(
        [{"text": c["text"], "metadata": dict(c["metadata"])} for c in chunks]
    )
    return {
        "ingestion_summary": {
            "status": "STORED_DONE",
            "chunks": count,
            "document_id": (state.get("ingestion_metadata") or {}).get("document_id", ""),
            "approval_status": "PENDING_REVIEW",
        },
        **record_timing(state, "store", started),
    }


def build_ingestion_graph(sink=None):
    from langgraph.graph import END, START, StateGraph

    from ..state import WorkflowState

    builder = StateGraph(WorkflowState)
    builder.add_node("clean", node_clean)
    builder.add_node("security_check", node_security_check)
    builder.add_node("split", node_split)
    builder.add_node("store", node_store if sink is None else
                     (lambda s: _store_with(s, sink)))

    builder.add_edge(START, "clean")
    builder.add_edge("clean", "security_check")
    builder.add_edge("security_check", "split")
    builder.add_edge("split", "store")
    builder.add_edge("store", END)
    return builder.compile()


def _store_with(state: dict, sink) -> dict:
    state = {**state, "_inject": {"sink": sink}}
    return node_store(state)


def run_ingestion(raw_text: str, metadata: dict[str, Any], sink=None) -> dict:
    result = build_ingestion_graph(sink).invoke({
        "raw_text": raw_text or "", "ingestion_metadata": dict(metadata or {}),
    })
    return result["ingestion_summary"]

# =====================================================================
# Astra DB — collection unique `admin_guide_chunks` (flows 02 + 04).
# Production : langchain-astradb + embeddings mistral-embed.
# Tests hors-ligne : InMemoryVectorSink (+ similarité cosinus locale).
# =====================================================================
from __future__ import annotations

import math
import time
from typing import Any, Protocol

from .. import config


class VectorSink(Protocol):
    def add_chunks(self, chunks: list[dict]) -> int: ...

    def search(self, query_vector: list[float], top_k: int = 12) -> list[dict]: ...


class AstraVectorSink:
    """Production sink : AstraDBVectorStore, même contrat que le flow
    Langflow (page_content = chunk text, metadata API/response)."""

    def __init__(self, store: Any, embeddings: Any) -> None:
        self._store = store
        self._embeddings = embeddings

    def add_chunks(self, chunks: list[dict]) -> int:
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        # requêtes d'embedding par lots (l'API Mistral refuse les lots
        # trop volumineux en tokens) ; un 429 (limite de débit) est
        # réessayé avec un délai croissant — une ingestion d'un code
        # entier envoie des dizaines de lots.
        batch = 32
        written = 0
        for i in range(0, len(texts), batch):
            for attempt in range(4):
                try:
                    self._store.add_texts(texts=texts[i:i + batch], metadatas=metadatas[i:i + batch])
                    written += len(texts[i:i + batch])
                    break
                except Exception as exc:  # noqa: BLE001 — retry débit
                    if attempt == 3 or "429" not in str(exc):
                        raise
                    time.sleep(20.0 * (attempt + 1))
        return written

    def search(self, query_vector: list[float], top_k: int = 12) -> list[dict]:
        docs = self._store.similarity_search_by_vector(query_vector, k=top_k)
        return [{"text": d.page_content, "metadata": dict(d.metadata or {})} for d in docs]

    @classmethod
    def from_settings(cls) -> "AstraVectorSink":
        from langchain_astradb import AstraDBVectorStore

        if not config.astra_ready():
            raise LookupError("ASTRA_DB_APPLICATION_TOKEN / ASTRA_DB_API_ENDPOINT not configured.")
        embeddings = _mistral_embeddings()
        store = AstraDBVectorStore(
            embedding=embeddings,
            collection_name=config.VECTOR_COLLECTION,
            api_endpoint=config.ASTRA_DB_API_ENDPOINT,
            token=config.ASTRA_DB_APPLICATION_TOKEN,
            namespace=config.ASTRA_DB_KEYSPACE or None,
        )
        return cls(store, embeddings)


class InMemoryVectorSink:
    """Double de test : liste simple + cosinus local."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, dict]] = []

    def add_chunks(self, chunks: list[dict]) -> int:
        self.rows.extend((c["text"], dict(c["metadata"])) for c in chunks)
        return len(chunks)

    def search(self, query_vector: list[float], top_k: int = 12) -> list[dict]:
        embedding = _identity_embedding
        scored = []
        for text, meta in self.rows:
            vec = embedding(text)
            score = _cosine(query_vector, vec)
            scored.append((score, {"text": text, "metadata": meta}))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:top_k]]


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a) or 1) * math.sqrt(sum(x * x for x in b) or 1)
    return num / den


def _identity_embedding(text: str) -> list[float]:
    """Embedding déterministe de secours (tests) : sac de mots -> vecteur
    de 64 bits dérivé du texte."""
    import hashlib

    vec = [0.0] * 64
    for token in text.lower().split():
        digest = hashlib.md5(token.encode()).digest()
        index = digest[0] % 64
        vec[index] += 1.0
    return vec


def _mistral_embeddings() -> Any:
    from langchain_mistralai import MistralAIEmbeddings

    return MistralAIEmbeddings(model=config.EMBEDDING_MODEL, api_key=config.MISTRAL_API_KEY)


def default_embeddings() -> Any:
    return _mistral_embeddings()

"""Ties an Embedder to a VectorStore to answer "find me the top-k chunks"."""

from __future__ import annotations

from rag_core.embeddings import Embedder
from rag_core.vector_store import SearchResult, VectorStore


class Retriever:
    def __init__(self, embedder: Embedder, vector_store: VectorStore, top_k: int = 3) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._top_k = top_k

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        sphere: str | None = None,
        technology: str | None = None,
    ) -> list[SearchResult]:
        vector = self._embedder.embed_one(query)
        return self._vector_store.search(
            vector, top_k=top_k or self._top_k, sphere=sphere, technology=technology
        )

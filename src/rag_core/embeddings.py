"""Embedding backends.

Only one implementation today (local sentence-transformers, free, CPU-only)
but it's behind an interface so an API-based embedder (OpenAI, Cohere) or a
remote HTTP embedder (e.g. one running on a phone over Tailscale) can be
added later without touching retriever.py or pipeline.py.

Failures (model fails to load, encode() throws) are logged and re-raised as
EmbeddingError so interfaces can catch one known type.
"""

from __future__ import annotations

import logging
from typing import Protocol

from rag_core.errors import EmbeddingError

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
        ...

    def embed_one(self, text: str) -> list[float]:
        """Convenience for a single query string."""
        ...


class SentenceTransformersEmbedder:
    """Local, free, CPU-friendly embedder using the sentence-transformers library.

    The model is loaded lazily on first use so importing this module (or
    rag_core generally) never triggers a model download.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            return self._model
        except Exception as exc:
            logger.exception("Failed to load embedding model '%s'", self._model_name)
            raise EmbeddingError(f"Could not load embedding model '{self._model_name}': {exc}") from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            model = self._load()
            vectors = model.encode(texts, normalize_embeddings=True)
            return [v.tolist() for v in vectors]
        except EmbeddingError:
            raise
        except Exception as exc:
            logger.exception("Embedding %d text(s) failed", len(texts))
            raise EmbeddingError(f"Failed to embed text: {exc}") from exc

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

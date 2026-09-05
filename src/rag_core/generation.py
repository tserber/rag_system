"""Optional answer-generation step on top of retrieved chunks.

Two implementations, switched by rag_core.config.GenerationMode:

- NullGenerator: v1 default. Does no LLM call at all, just formats the
  retrieved chunks. This is what "output is retrieved data from Qdrant"
  means literally.
- OllamaGenerator: calls a local Ollama server to synthesize a short answer
  from the retrieved chunks. Free, private, needs `ollama serve` running
  with the configured model pulled. Failures are logged and re-raised as
  GenerationUnavailableError so interfaces can catch one known type
  (e.g. to say "Ollama is not reachable" instead of crashing).
"""

from __future__ import annotations

import logging
from typing import Protocol

from rag_core.errors import GenerationUnavailableError
from rag_core.vector_store import SearchResult

logger = logging.getLogger(__name__)


class Generator(Protocol):
    def generate(self, query: str, chunks: list[SearchResult]) -> str | None:
        """Return a generated answer, or None if this generator doesn't produce one."""
        ...


class NullGenerator:
    def generate(self, query: str, chunks: list[SearchResult]) -> str | None:
        return None


class OllamaGenerator:
    def __init__(self, host: str, model: str) -> None:
        self._host = host.rstrip("/")
        self._model = model

    def generate(self, query: str, chunks: list[SearchResult]) -> str | None:
        import requests

        context = "\n\n".join(f"[{i + 1}] {c.text}" for i, c in enumerate(chunks))
        prompt = (
            "Answer the question using only the context below. "
            "If the context doesn't contain the answer, say so.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        )
        try:
            response = requests.post(
                f"{self._host}/api/generate",
                json={"model": self._model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.RequestException as exc:
            logger.exception("Ollama generation failed (host=%s, model=%s)", self._host, self._model)
            raise GenerationUnavailableError(
                f"Could not reach Ollama at {self._host} (model '{self._model}'): {exc}"
            ) from exc

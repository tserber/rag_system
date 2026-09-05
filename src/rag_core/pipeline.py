"""RagPipeline: the one class every interface (Telegram, FastAPI, Django) calls.

Nothing in this file knows about Telegram, HTTP, or any web framework. An
interface's entire job is: get a query string in from its own transport,
call `pipeline.query(text)`, and format `RagResponse` back out through that
same transport.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from rag_core.config import GenerationMode, Settings, get_settings
from rag_core.embeddings import Embedder, SentenceTransformersEmbedder
from rag_core.errors import RagCoreError
from rag_core.generation import Generator, NullGenerator, OllamaGenerator
from rag_core.retriever import Retriever
from rag_core.vector_store import QdrantVectorStore, VectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    score: float
    metadata: dict


@dataclass(frozen=True)
class RagResponse:
    query: str
    chunks: list[RetrievedChunk]
    answer: str | None  # None when running in retrieval-only mode


class RagPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        generator: Generator | None = None,
    ) -> None:
        """All dependencies are optional and default to the configured
        implementations, but can be swapped for fakes in tests or for a
        future alternative backend (e.g. a remote embedder on a phone).
        """
        self._settings = settings or get_settings()
        self._embedder = embedder or SentenceTransformersEmbedder(self._settings.embedding_model)
        self._vector_store = vector_store or QdrantVectorStore(self._settings)
        self._retriever = Retriever(self._embedder, self._vector_store, top_k=self._settings.top_k)
        self._generator = generator or self._build_generator()

    def _build_generator(self) -> Generator:
        if self._settings.generation_mode == GenerationMode.OLLAMA:
            return OllamaGenerator(self._settings.ollama_host, self._settings.ollama_model)
        return NullGenerator()

    def query(
        self,
        text: str,
        top_k: int | None = None,
        sphere: str | None = None,
        technology: str | None = None,
    ) -> RagResponse:
        """Filtering by sphere/technology is optional and additive: leave both
        None to search everything, as the Telegram bot does today.

        Raises rag_core.errors.RagCoreError (or a subclass) if the embedder,
        vector store, or generator is unavailable. Callers (interfaces)
        should catch that and reply/respond accordingly rather than let it
        propagate as an unhandled exception.
        """
        logger.debug("Query received: %r (top_k=%s, sphere=%s, technology=%s)", text, top_k, sphere, technology)
        try:
            results = self._retriever.retrieve(text, top_k=top_k, sphere=sphere, technology=technology)
            answer = self._generator.generate(text, results)
        except RagCoreError:
            logger.warning("Query failed due to a known dependency error: %r", text)
            raise
        chunks = [RetrievedChunk(text=r.text, score=r.score, metadata=r.metadata) for r in results]
        logger.debug("Query %r returned %d chunk(s)", text, len(chunks))
        return RagResponse(query=text, chunks=chunks, answer=answer)

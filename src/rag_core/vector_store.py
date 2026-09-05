"""Qdrant wrapper that hides the local-vs-cloud switch behind one interface.

rag_core.config.QdrantMode picks which client gets built; nothing above this
module (retriever, pipeline, interfaces) needs to know or care which one is
active. This is also the seam where you could later swap in a completely
different vector DB by writing another class with the same methods.

Every public method catches failures from the underlying qdrant-client call
(connection refused, timeout, bad response, ...) and re-raises them as
VectorStoreUnavailableError, after logging the original exception. Interfaces
catch that one type and don't need to know anything about qdrant-client's
own exception hierarchy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from rag_core.config import QdrantMode, Settings
from rag_core.errors import VectorStoreUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    text: str
    score: float
    metadata: dict


class VectorStore(Protocol):
    def ensure_collection(self, vector_size: int) -> None: ...

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None: ...

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        sphere: str | None = None,
        technology: str | None = None,
    ) -> list[SearchResult]: ...


class QdrantVectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def _load_client(self):
        if self._client is not None:
            return self._client

        from qdrant_client import QdrantClient

        s = self._settings
        if s.qdrant_mode == QdrantMode.CLOUD:
            if not s.qdrant_cloud_url:
                raise ValueError("qdrant_cloud_url must be set when QDRANT_MODE=cloud")
            self._client = QdrantClient(url=s.qdrant_cloud_url, api_key=s.qdrant_cloud_api_key)
        else:
            self._client = QdrantClient(host=s.qdrant_local_host, port=s.qdrant_local_port)
        return self._client

    def ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        try:
            client = self._load_client()
            collection = self._settings.qdrant_collection
            existing = {c.name for c in client.get_collections().collections}
            if collection not in existing:
                client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except Exception as exc:
            logger.exception("Failed to ensure Qdrant collection '%s' exists", self._settings.qdrant_collection)
            raise VectorStoreUnavailableError(
                f"Could not reach Qdrant to prepare collection '{self._settings.qdrant_collection}': {exc}"
            ) from exc

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None:
        from qdrant_client.models import PointStruct

        try:
            client = self._load_client()
            points = [
                PointStruct(id=i, vector=v, payload=p)
                for i, v, p in zip(ids, vectors, payloads, strict=True)
            ]
            client.upsert(collection_name=self._settings.qdrant_collection, points=points)
        except Exception as exc:
            logger.exception("Failed to upsert %d points into Qdrant", len(ids))
            raise VectorStoreUnavailableError(f"Could not write to Qdrant: {exc}") from exc

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        sphere: str | None = None,
        technology: str | None = None,
    ) -> list[SearchResult]:
        try:
            client = self._load_client()
            query_filter = self._build_filter(sphere, technology)
            hits = client.query_points(
                collection_name=self._settings.qdrant_collection,
                query=query_vector,
                limit=top_k,
                query_filter=query_filter,
            ).points
            return [
                SearchResult(text=hit.payload.get("text", ""), score=hit.score, metadata=hit.payload)
                for hit in hits
            ]
        except VectorStoreUnavailableError:
            raise
        except Exception as exc:
            logger.exception("Qdrant search failed")
            raise VectorStoreUnavailableError(f"Could not reach Qdrant to search: {exc}") from exc

    @staticmethod
    def _build_filter(sphere: str | None, technology: str | None):
        if sphere is None and technology is None:
            return None

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        conditions = []
        if sphere is not None:
            conditions.append(FieldCondition(key="sphere", match=MatchValue(value=sphere)))
        if technology is not None:
            conditions.append(FieldCondition(key="technology", match=MatchValue(value=technology)))
        return Filter(must=conditions)

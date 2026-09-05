"""End-to-end retrieval test: real ingest_folder, real chunking, real metadata
inference, real qdrant-client (embedded ":memory:" engine, no Docker needed),
and a handful of real natural-language questions asked through RagPipeline.

The one thing NOT real here is the embedding model: sentence-transformers
needs a model download, which this test suite deliberately avoids so it runs
anywhere with no network. Instead this uses a tiny offline bag-of-words
embedder defined below -- a genuine (if crude) embedding where shared words
between texts produce closer vectors, so the retrieval assertions below are
meaningful, not hardcoded.

This is deliberately a separate file from test_pipeline.py: that one checks
RagPipeline's wiring with fully scripted fakes; this one checks that the real
ingestion path and the real vector_store filtering logic actually retrieve
the right document for a real question.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import pytest

qdrant_client = pytest.importorskip("qdrant_client")

from rag_core import ingest as ingest_module
from rag_core.config import GenerationMode, QdrantMode, Settings
from rag_core.generation import NullGenerator
from rag_core.pipeline import RagPipeline
from rag_core.vector_store import QdrantVectorStore

FIXTURES = Path(__file__).parent / "fixtures" / "sample_docs"
DIM = 256


def _embed_text(text: str) -> list[float]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    vector = [0.0] * DIM
    for word in words:
        idx = int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIM
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class BagOfWordsEmbedder:
    """Offline stand-in for SentenceTransformersEmbedder, used only in this
    test file. Never use this for real ingestion -- it has no real semantic
    understanding, just word overlap.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_embed_text(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return _embed_text(text)


@pytest.fixture
def ingested_pipeline(monkeypatch):
    settings = Settings(
        qdrant_mode=QdrantMode.LOCAL,
        generation_mode=GenerationMode.RETRIEVAL_ONLY,
        top_k=3,
        _env_file=None,
    )
    embedder = BagOfWordsEmbedder()
    store = QdrantVectorStore(settings)
    store._client = qdrant_client.QdrantClient(":memory:")  # embedded engine, no Docker

    # Run the real ingest_folder function against the real fixture files,
    # only swapping the heavy objects it constructs internally.
    monkeypatch.setattr(ingest_module, "SentenceTransformersEmbedder", lambda model_name: embedder)
    monkeypatch.setattr(ingest_module, "QdrantVectorStore", lambda settings: store)
    monkeypatch.setattr(ingest_module, "get_settings", lambda: settings)
    chunk_count = ingest_module.ingest_folder(FIXTURES)
    assert chunk_count > 0, "fixture ingestion produced no chunks"

    return RagPipeline(settings=settings, embedder=embedder, vector_store=store, generator=NullGenerator())


@pytest.mark.parametrize(
    "question, expected_technology",
    [
        ("What does Postgres use for concurrency control?", "postgresql"),
        ("What kind of database is MongoDB, document or relational?", "mongodb"),
        ("Why is Redis fast, and what's the tradeoff?", "redis"),
        ("How does DNS resolve a domain name to an IP address?", None),
    ],
)
def test_question_retrieves_expected_document(ingested_pipeline, question, expected_technology):
    response = ingested_pipeline.query(question, top_k=2)
    assert response.chunks, f"no results for {question!r}"
    top = response.chunks[0]
    if expected_technology is not None:
        assert top.metadata.get("technology") == expected_technology, (
            f"expected top match for {question!r} to be about {expected_technology!r}, "
            f"got {top.metadata.get('technology')!r}: {top.text[:80]!r}"
        )


def test_technology_filter_excludes_other_technologies(ingested_pipeline):
    response = ingested_pipeline.query("How does it store data?", top_k=5, technology="postgresql")
    assert response.chunks, "filtered query returned nothing"
    assert all(c.metadata.get("technology") == "postgresql" for c in response.chunks)


def test_sphere_filter_excludes_other_spheres(ingested_pipeline):
    response = ingested_pipeline.query("Tell me something", top_k=10, sphere="databases")
    assert response.chunks, "sphere-filtered query returned nothing"
    assert all(c.metadata.get("sphere") == "databases" for c in response.chunks)

"""Pipeline test using fakes for the embedder and vector store, so it runs
without downloading a model or needing a live Qdrant/Ollama instance.
"""

from rag_core.config import GenerationMode, QdrantMode, Settings
from rag_core.generation import NullGenerator
from rag_core.pipeline import RagPipeline
from rag_core.vector_store import SearchResult


class FakeEmbedder:
    def embed(self, texts):
        return [[0.0] for _ in texts]

    def embed_one(self, text):
        return [0.0]


class FakeVectorStore:
    def ensure_collection(self, vector_size):
        pass

    def upsert(self, ids, vectors, payloads):
        pass

    def search(self, query_vector, top_k, sphere=None, technology=None):
        results = [
            SearchResult(
                text="Warsaw is the capital of Poland.",
                score=0.91,
                metadata={"source": "facts.md", "sphere": None, "technology": None},
            ),
            SearchResult(
                text="Postgres uses MVCC for concurrency.",
                score=0.77,
                metadata={"source": "databases/postgresql/mvcc.md", "sphere": "databases", "technology": "postgresql"},
            ),
        ]
        if technology is not None:
            results = [r for r in results if r.metadata.get("technology") == technology]
        if sphere is not None:
            results = [r for r in results if r.metadata.get("sphere") == sphere]
        return results[:top_k]


def build_test_settings() -> Settings:
    return Settings(
        qdrant_mode=QdrantMode.LOCAL,
        generation_mode=GenerationMode.RETRIEVAL_ONLY,
        top_k=3,
        _env_file=None,
    )


def test_retrieval_only_mode_returns_no_answer():
    pipeline = RagPipeline(
        settings=build_test_settings(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        generator=NullGenerator(),
    )

    response = pipeline.query("What is Qdrant?")

    assert response.answer is None
    assert len(response.chunks) == 2
    assert response.chunks[0].text == "Warsaw is the capital of Poland."
    assert response.chunks[0].score == 0.91


def test_top_k_is_respected():
    pipeline = RagPipeline(
        settings=build_test_settings(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        generator=NullGenerator(),
    )

    response = pipeline.query("What is Qdrant?", top_k=1)

    assert len(response.chunks) == 1


def test_technology_filter_narrows_results():
    pipeline = RagPipeline(
        settings=build_test_settings(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        generator=NullGenerator(),
    )

    response = pipeline.query("How does concurrency work?", technology="postgresql")

    assert len(response.chunks) == 1
    assert response.chunks[0].metadata["technology"] == "postgresql"

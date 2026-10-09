"""Ingest tests using fake embedder/vector-store classes (same approach as
test_pipeline.py) plus real temp files on disk, so this runs offline and
without a live Qdrant/model -- focused on proving re-ingesting a folder is
idempotent (same chunk -> same Qdrant point ID every time), not duplicated.
"""

from __future__ import annotations

import rag_core.ingest as ingest_module
from rag_core.ingest import _stable_chunk_id, ingest_folder


class FakeEmbedder:
    def __init__(self, model_name) -> None:
        pass

    def embed(self, texts):
        return [[0.0, 0.0] for _ in texts]

    def embed_one(self, text):
        return [0.0, 0.0]


class FakeVectorStore:
    """Records every upsert call so a test can inspect exactly which IDs
    were written, across multiple ingest_folder() calls."""

    def __init__(self, settings) -> None:
        self.upserts: list[dict] = []

    def ensure_collection(self, vector_size):
        pass

    def upsert(self, ids, vectors, payloads):
        self.upserts.append({"ids": list(ids), "payloads": list(payloads)})


def test_stable_chunk_id_is_deterministic_for_the_same_source_and_index():
    first = _stable_chunk_id("data/notes.md", 0)
    second = _stable_chunk_id("data/notes.md", 0)
    assert first == second


def test_stable_chunk_id_differs_by_chunk_index():
    assert _stable_chunk_id("data/notes.md", 0) != _stable_chunk_id("data/notes.md", 1)


def test_stable_chunk_id_differs_by_source():
    assert _stable_chunk_id("data/a.md", 0) != _stable_chunk_id("data/b.md", 0)


def test_reingesting_an_unchanged_folder_upserts_the_same_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_module, "SentenceTransformersEmbedder", FakeEmbedder)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "notes.md").write_text("Some notes about Postgres indexing.")

    stores: list[FakeVectorStore] = []

    def tracking_store(settings):
        store = FakeVectorStore(settings)
        stores.append(store)
        return store

    monkeypatch.setattr(ingest_module, "QdrantVectorStore", tracking_store)

    ingest_folder(data_dir)
    ingest_folder(data_dir)

    assert len(stores) == 2
    first_ids = stores[0].upserts[0]["ids"]
    second_ids = stores[1].upserts[0]["ids"]
    assert first_ids == second_ids  # same chunks -> same points, not duplicated


def test_editing_a_file_keeps_the_same_ids_for_its_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_module, "SentenceTransformersEmbedder", FakeEmbedder)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    note_path = data_dir / "notes.md"
    note_path.write_text("Original content.")

    stores: list[FakeVectorStore] = []

    def tracking_store(settings):
        store = FakeVectorStore(settings)
        stores.append(store)
        return store

    monkeypatch.setattr(ingest_module, "QdrantVectorStore", tracking_store)

    ingest_folder(data_dir)
    note_path.write_text("Edited content, still one chunk.")
    ingest_folder(data_dir)

    first_ids = stores[0].upserts[0]["ids"]
    second_ids = stores[1].upserts[0]["ids"]
    assert first_ids == second_ids  # same (source, chunk_index) -> updates in place
    # but the payload text actually changed
    assert stores[0].upserts[0]["payloads"][0]["text"] != stores[1].upserts[0]["payloads"][0]["text"]

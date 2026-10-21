"""Ingest tests using fake embedder/vector-store classes (same approach as
test_pipeline.py) plus real temp files on disk, so this runs offline and
without a live Qdrant/model -- focused on proving re-ingesting a folder is
idempotent (same chunk -> same Qdrant point ID every time), not duplicated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import rag_core.ingest as ingest_module
from rag_core.ingest import Ingester, _stable_chunk_id, ingest_folder


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


class FakeStrategy:
    """A custom, test-only ingest strategy -- proves Ingester works with
    whatever strategy list it's given, not just the two built-in ones."""

    kind = "fake"

    def __init__(self, extension: str, text: str) -> None:
        self._extension = extension
        self._text = text

    def can_handle(self, path: Path) -> bool:
        return path.suffix == self._extension

    def extract_text(self, path: Path) -> str:
        return self._text


def test_ingester_accepts_a_custom_strategy_list(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "weird.xyz").write_text("ignored by the fake strategy -- it returns fixed text")

    store = FakeVectorStore(settings=None)
    ingester = Ingester(
        strategies=[FakeStrategy(extension=".xyz", text="hello from a custom strategy")],
        embedder=FakeEmbedder(model_name=""),
        vector_store=store,
    )

    count = ingester.ingest_folder(data_dir)

    assert count == 1
    assert store.upserts[0]["payloads"][0]["text"] == "hello from a custom strategy"
    assert store.upserts[0]["payloads"][0]["kind"] == "fake"


def test_ingester_skips_files_no_strategy_claims(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "unrelated.bin").write_bytes(b"\x00\x01")  # no strategy handles .bin

    store = FakeVectorStore(settings=None)
    ingester = Ingester(
        strategies=[FakeStrategy(extension=".xyz", text="irrelevant")],
        embedder=FakeEmbedder(model_name=""),
        vector_store=store,
    )

    count = ingester.ingest_folder(data_dir)

    assert count == 0
    assert store.upserts == []  # never even reached the embed/upsert step


def test_ingest_file_indexes_a_single_file(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("Standalone note about Qdrant filtering.")

    store = FakeVectorStore(settings=None)
    ingester = Ingester(
        strategies=[FakeStrategy(extension=".md", text="Standalone note about Qdrant filtering.")],
        embedder=FakeEmbedder(model_name=""),
        vector_store=store,
    )

    count = ingester.ingest_file(path)

    assert count == 1
    assert store.upserts[0]["payloads"][0]["source"] == str(path)
    assert store.upserts[0]["payloads"][0]["text"] == "Standalone note about Qdrant filtering."


def test_ingest_file_raises_on_unsupported_type(tmp_path):
    path = tmp_path / "unknown.bin"
    path.write_bytes(b"\x00\x01")

    ingester = Ingester(
        strategies=[FakeStrategy(extension=".xyz", text="irrelevant")],
        embedder=FakeEmbedder(model_name=""),
        vector_store=FakeVectorStore(settings=None),
    )

    with pytest.raises(ValueError, match="unsupported file type"):
        ingester.ingest_file(path)


def test_ingest_file_reuses_the_same_stable_id_as_ingest_folder(tmp_path):
    """ingest_file and ingest_folder must agree on the ID for the same
    chunk of the same file, or dropping a file onto the desktop app and
    later re-ingesting the whole data/ folder would create a duplicate
    instead of updating the same point."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    path = data_dir / "notes.md"
    path.write_text("shared content")

    strategy = FakeStrategy(extension=".md", text="shared content")

    folder_store = FakeVectorStore(settings=None)
    Ingester(strategies=[strategy], embedder=FakeEmbedder(model_name=""), vector_store=folder_store).ingest_folder(
        data_dir
    )

    file_store = FakeVectorStore(settings=None)
    Ingester(strategies=[strategy], embedder=FakeEmbedder(model_name=""), vector_store=file_store).ingest_file(path)

    assert folder_store.upserts[0]["ids"] == file_store.upserts[0]["ids"]

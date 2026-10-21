"""Chunk, embed, and index files from a folder into Qdrant, using whichever
IngestStrategy (see rag_core.ingest_strategies) claims each file.

Usage:
    python -m rag_core.ingest ./data

Files are organized as data/<sphere>/<technology>/*.{md,txt,mp3,wav,...} so
sphere and technology metadata get inferred automatically -- see
rag_core.metadata. Source-type handling (text file vs. audio file, and
whatever gets added later) lives entirely in rag_core.ingest_strategies;
Ingester just picks a strategy per file and runs the same chunk/embed/
upsert pipeline regardless of what produced the text.

Re-running this on a folder you've already ingested is safe: each chunk's
Qdrant point ID is derived deterministically from (source path, chunk
index), not randomly generated, so upserting the same file again overwrites
the same points instead of duplicating them -- add one new file and
re-ingest the whole data/ folder, nothing already indexed gets duplicated.
Editing a file's content updates its existing points in place the next time
you ingest. One known limitation: if an edit *shrinks* a file enough to
produce fewer chunks than before, the extra old chunks (now orphaned) stay
in Qdrant rather than being cleaned up -- rebuilding the collection
(`docker compose down -v && docker compose up -d qdrant`, then re-ingest)
is the way to fully reconcile if that happens often enough to matter.
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

from rag_core.chunking import chunk_text
from rag_core.config import Settings, get_settings
from rag_core.embeddings import Embedder, SentenceTransformersEmbedder
from rag_core.errors import RagCoreError
from rag_core.ingest_strategies import (
    AudioFileStrategy,
    IngestStrategy,
    TextFileStrategy,
)
from rag_core.logging_config import configure_logging
from rag_core.metadata import ChunkMetadata, infer_sphere_and_technology
from rag_core.transcription import FasterWhisperTranscriber
from rag_core.vector_store import QdrantVectorStore, VectorStore

logger = logging.getLogger(__name__)

# Fixed on purpose -- do not regenerate. uuid5(NAMESPACE, name) is only
# deterministic across runs if NAMESPACE itself never changes; changing it
# would silently re-randomize every chunk ID and duplicate your whole
# collection on the next ingest.
_CHUNK_ID_NAMESPACE = uuid.UUID("45bbec77-10d0-47bb-93a4-17bbe01d564e")


def _stable_chunk_id(source: str, chunk_index: int) -> str:
    """A Qdrant point ID that's the same every time for the same chunk of
    the same file, so upserting is idempotent instead of ever-growing."""
    return str(uuid.uuid5(_CHUNK_ID_NAMESPACE, f"{source}::{chunk_index}"))


class Ingester:
    """Orchestrates ingestion: walk a folder, pick an IngestStrategy per
    file, chunk/embed/upsert the result. Owns no source-type-specific
    logic itself -- see rag_core.ingest_strategies for that -- so adding a
    new source type never means touching this class.

    All dependencies are optional and default to the configured
    implementations, same pattern as RagPipeline, so tests can swap in
    fakes and a future caller can swap in a different embedder/vector
    store or a custom strategy list (e.g. PDF-only ingestion) without
    subclassing anything.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        strategies: list[IngestStrategy] | None = None,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._strategies = strategies if strategies is not None else self._default_strategies()
        self._embedder = embedder or SentenceTransformersEmbedder(self._settings.embedding_model)
        self._vector_store = vector_store or QdrantVectorStore(self._settings)

    def _default_strategies(self) -> list[IngestStrategy]:
        settings = self._settings
        return [
            TextFileStrategy(),
            AudioFileStrategy(
                lambda: FasterWhisperTranscriber(
                    model_size=settings.whisper_model_size,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
            ),
        ]

    def _strategy_for(self, path: Path) -> IngestStrategy | None:
        for strategy in self._strategies:
            if strategy.can_handle(path):
                return strategy
        return None

    def _chunks_for_file(self, path: Path, root: Path) -> list[tuple[str, dict]]:
        """Extract + chunk one file into (text, metadata payload) pairs.
        Shared by ingest_folder (which batches many files into one embed
        call) and ingest_file (which embeds just this one) -- the part
        worth keeping DRY is picking a strategy and building metadata, not
        how the caller batches the embed/upsert step."""
        strategy = self._strategy_for(path)
        if strategy is None:
            return []

        sphere, technology = infer_sphere_and_technology(path, root)
        logger.info("Extracting %s via %s ...", path, type(strategy).__name__)
        content = strategy.extract_text(path)

        chunks: list[tuple[str, dict]] = []
        for chunk in chunk_text(content, self._settings.chunk_size_chars, self._settings.chunk_overlap_chars):
            metadata = ChunkMetadata(
                text=chunk.text,
                source=str(path),
                chunk_index=chunk.index,
                sphere=sphere,
                technology=technology,
                kind=strategy.kind,
            )
            chunks.append((chunk.text, metadata.to_payload()))
        return chunks

    def ingest_folder(self, folder: Path) -> int:
        files = [p for p in folder.rglob("*") if p.is_file()]
        if not files:
            logger.warning("No files found under %s", folder)
            return 0

        all_chunks: list[tuple[str, dict]] = []  # (text, metadata payload)
        matched_files = 0
        for path in files:
            if self._strategy_for(path) is None:
                continue  # not an error -- .DS_Store, a README, anything no strategy claims
            matched_files += 1
            try:
                all_chunks.extend(self._chunks_for_file(path, folder))
            except OSError:
                # A single unreadable file (permissions, encoding surprise, ...)
                # shouldn't abort ingesting everything else.
                logger.exception("Skipping unreadable file: %s", path)
                continue
            except RagCoreError:
                # A single file that fails to process (bad audio, missing
                # faster-whisper) shouldn't abort ingesting everything else
                # either -- log it and move on, same reasoning as OSError above.
                logger.exception("Skipping file that failed to process: %s", path)
                continue

        if not all_chunks:
            logger.warning("Files were found but produced no chunks (nothing matched a strategy, or empty content?).")
            return 0

        count = self._embed_and_upsert(all_chunks)
        logger.info(
            "Ingested %d chunks from %d files into '%s'.", count, matched_files, self._settings.qdrant_collection
        )
        return count

    def ingest_file(self, path: Path) -> int:
        """Ingest exactly one file -- the single-file counterpart to
        ingest_folder, for callers (like a drag-and-drop UI) that process
        one user-selected file at a time rather than a whole directory.

        Raises ValueError if no strategy recognizes the file's type, so a
        caller can show a clear "unsupported file" message instead of
        silently doing nothing (ingest_folder skips unmatched files
        silently, since skimming a whole directory for whatever it
        recognizes is the expected behavior there; a single file a user
        explicitly chose warrants an explicit error instead).
        """
        if self._strategy_for(path) is None:
            raise ValueError(f"No ingest strategy can handle '{path.name}' (unsupported file type)")

        chunks = self._chunks_for_file(path, path.parent)
        if not chunks:
            logger.warning("File produced no chunks (empty content?): %s", path)
            return 0

        count = self._embed_and_upsert(chunks)
        logger.info("Ingested %d chunks from '%s' into '%s'.", count, path.name, self._settings.qdrant_collection)
        return count

    def _embed_and_upsert(self, chunks: list[tuple[str, dict]]) -> int:
        texts = [c[0] for c in chunks]
        try:
            vectors = self._embedder.embed(texts)
            self._vector_store.ensure_collection(vector_size=len(vectors[0]))
            payloads = [c[1] for c in chunks]
            ids = [_stable_chunk_id(p["source"], p["chunk_index"]) for p in payloads]
            self._vector_store.upsert(ids=ids, vectors=vectors, payloads=payloads)
        except RagCoreError:
            logger.exception("Ingestion failed while embedding or writing to Qdrant")
            raise
        return len(chunks)


def ingest_folder(folder: Path) -> int:
    """Module-level convenience wrapper around Ingester(), for the CLI and
    for callers that don't need to customize strategies/embedder/store."""
    return Ingester().ingest_folder(folder)


def main() -> None:
    configure_logging()
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")
    ingest_folder(folder)


if __name__ == "__main__":
    main()

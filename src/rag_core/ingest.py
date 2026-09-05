"""Load .txt/.md files from a folder, chunk them, embed them, upsert to Qdrant.

Usage:
    python -m rag_core.ingest ./data

Files are organized as data/<sphere>/<technology>/*.{md,txt} so sphere and
technology metadata get inferred automatically -- see rag_core.metadata.
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

from rag_core.chunking import chunk_text
from rag_core.config import get_settings
from rag_core.embeddings import SentenceTransformersEmbedder
from rag_core.errors import RagCoreError
from rag_core.logging_config import configure_logging
from rag_core.metadata import ChunkMetadata, infer_sphere_and_technology
from rag_core.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)


def ingest_folder(folder: Path) -> int:
    settings = get_settings()
    embedder = SentenceTransformersEmbedder(settings.embedding_model)
    store = QdrantVectorStore(settings)

    files = [p for p in folder.rglob("*") if p.suffix.lower() in {".txt", ".md"}]
    if not files:
        logger.warning("No .txt/.md files found under %s", folder)
        return 0

    all_chunks: list[tuple[str, dict]] = []  # (text, metadata payload)
    for path in files:
        try:
            sphere, technology = infer_sphere_and_technology(path, folder)
            content = path.read_text(encoding="utf-8", errors="ignore")
            for chunk in chunk_text(content, settings.chunk_size_chars, settings.chunk_overlap_chars):
                metadata = ChunkMetadata(
                    text=chunk.text,
                    source=str(path),
                    chunk_index=chunk.index,
                    sphere=sphere,
                    technology=technology,
                )
                all_chunks.append((chunk.text, metadata.to_payload()))
        except OSError:
            # A single unreadable file (permissions, encoding surprise, ...)
            # shouldn't abort ingesting everything else.
            logger.exception("Skipping unreadable file: %s", path)
            continue

    if not all_chunks:
        logger.warning("Files were found but produced no chunks (empty content?).")
        return 0

    texts = [c[0] for c in all_chunks]
    try:
        vectors = embedder.embed(texts)
        store.ensure_collection(vector_size=len(vectors[0]))
        ids = [str(uuid.uuid4()) for _ in all_chunks]
        payloads = [c[1] for c in all_chunks]
        store.upsert(ids=ids, vectors=vectors, payloads=payloads)
    except RagCoreError:
        logger.exception("Ingestion failed while embedding or writing to Qdrant")
        raise

    logger.info(
        "Ingested %d chunks from %d files into '%s'.", len(all_chunks), len(files), settings.qdrant_collection
    )
    return len(all_chunks)


def main() -> None:
    configure_logging()
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")
    ingest_folder(folder)


if __name__ == "__main__":
    main()

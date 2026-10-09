"""Load .txt/.md files (and audio files, transcribed first) from a folder,
chunk them, embed them, upsert to Qdrant.

Usage:
    python -m rag_core.ingest ./data

Files are organized as data/<sphere>/<technology>/*.{md,txt,mp3,wav,...} so
sphere and technology metadata get inferred automatically -- see
rag_core.metadata. Audio files (see rag_core.transcription.AUDIO_EXTENSIONS)
are transcribed to text before chunking; everything downstream of that
(chunking, embedding, metadata, upsert) is identical for text and audio
sources, they just end up tagged with a different `kind` in the payload.

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
from rag_core.config import get_settings
from rag_core.embeddings import SentenceTransformersEmbedder
from rag_core.errors import RagCoreError
from rag_core.logging_config import configure_logging
from rag_core.metadata import ChunkMetadata, infer_sphere_and_technology
from rag_core.transcription import AUDIO_EXTENSIONS, FasterWhisperTranscriber
from rag_core.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {".txt", ".md"}

# Fixed on purpose -- do not regenerate. uuid5(NAMESPACE, name) is only
# deterministic across runs if NAMESPACE itself never changes; changing it
# would silently re-randomize every chunk ID and duplicate your whole
# collection on the next ingest.
_CHUNK_ID_NAMESPACE = uuid.UUID("45bbec77-10d0-47bb-93a4-17bbe01d564e")


def _stable_chunk_id(source: str, chunk_index: int) -> str:
    """A Qdrant point ID that's the same every time for the same chunk of
    the same file, so upserting is idempotent instead of ever-growing."""
    return str(uuid.uuid5(_CHUNK_ID_NAMESPACE, f"{source}::{chunk_index}"))


def ingest_folder(folder: Path) -> int:
    settings = get_settings()
    embedder = SentenceTransformersEmbedder(settings.embedding_model)
    store = QdrantVectorStore(settings)
    # Built lazily (see below) so machines with no audio files in `folder`
    # never need the optional `faster-whisper` dependency installed.
    transcriber: FasterWhisperTranscriber | None = None

    files = [p for p in folder.rglob("*") if p.suffix.lower() in TEXT_EXTENSIONS | AUDIO_EXTENSIONS]
    if not files:
        logger.warning("No .txt/.md/audio files found under %s", folder)
        return 0

    all_chunks: list[tuple[str, dict]] = []  # (text, metadata payload)
    for path in files:
        try:
            sphere, technology = infer_sphere_and_technology(path, folder)
            is_audio = path.suffix.lower() in AUDIO_EXTENSIONS
            if is_audio:
                if transcriber is None:
                    transcriber = FasterWhisperTranscriber(
                        model_size=settings.whisper_model_size,
                        device=settings.whisper_device,
                        compute_type=settings.whisper_compute_type,
                    )
                logger.info("Transcribing %s ...", path)
                content = transcriber.transcribe(path)
                kind = "audio_transcript"
            else:
                content = path.read_text(encoding="utf-8", errors="ignore")
                kind = "text"

            for chunk in chunk_text(content, settings.chunk_size_chars, settings.chunk_overlap_chars):
                metadata = ChunkMetadata(
                    text=chunk.text,
                    source=str(path),
                    chunk_index=chunk.index,
                    sphere=sphere,
                    technology=technology,
                    kind=kind,
                )
                all_chunks.append((chunk.text, metadata.to_payload()))
        except OSError:
            # A single unreadable file (permissions, encoding surprise, ...)
            # shouldn't abort ingesting everything else.
            logger.exception("Skipping unreadable file: %s", path)
            continue
        except RagCoreError:
            # A single file that fails to transcribe (bad audio, missing
            # faster-whisper) shouldn't abort ingesting everything else
            # either -- log it and move on, same reasoning as OSError above.
            logger.exception("Skipping file that failed to process: %s", path)
            continue

    if not all_chunks:
        logger.warning("Files were found but produced no chunks (empty content?).")
        return 0

    texts = [c[0] for c in all_chunks]
    try:
        vectors = embedder.embed(texts)
        store.ensure_collection(vector_size=len(vectors[0]))
        payloads = [c[1] for c in all_chunks]
        ids = [_stable_chunk_id(p["source"], p["chunk_index"]) for p in payloads]
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

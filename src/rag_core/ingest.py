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

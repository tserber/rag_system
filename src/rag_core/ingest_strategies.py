"""Pluggable ingest strategies: each one owns "can I handle this file, and
how do I turn it into plain text" for one source type. Same
Protocol-with-swappable-implementations pattern already used for Embedder,
VectorStore, and Generator (see agents.md) -- adding a new source type
(PDF, HTML, a URL fetcher, a Notion export) means writing one new class
here, never touching Ingester's control flow in ingest.py.

Strategies are tried in order; the first one whose can_handle() returns
True wins. A file that no strategy claims is skipped, not an error -- that
covers directories, .DS_Store, and anything else that isn't actually
ingestible content.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from rag_core.transcription import AUDIO_EXTENSIONS, FasterWhisperTranscriber

TEXT_EXTENSIONS = {".txt", ".md"}


class IngestStrategy(Protocol):
    kind: str  # tagged on every chunk's metadata, see rag_core.metadata.ChunkMetadata

    def can_handle(self, path: Path) -> bool:
        """Whether this strategy knows how to extract text from `path`."""
        ...

    def extract_text(self, path: Path) -> str:
        """Return the raw text content to chunk, embed, and index."""
        ...


class TextFileStrategy:
    """Plain .txt/.md files, read as-is."""

    kind = "text"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in TEXT_EXTENSIONS

    def extract_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")


class AudioFileStrategy:
    """Audio files, transcribed to text first (see rag_core.transcription).

    The transcriber is built lazily via a factory, not eagerly in
    __init__, so constructing this strategy never requires the optional
    `faster-whisper` dependency unless an audio file is actually seen --
    same reasoning as FasterWhisperTranscriber's own lazy model loading.
    """

    kind = "audio_transcript"

    def __init__(self, transcriber_factory: Callable[[], FasterWhisperTranscriber]) -> None:
        self._transcriber_factory = transcriber_factory
        self._transcriber: FasterWhisperTranscriber | None = None

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in AUDIO_EXTENSIONS

    def extract_text(self, path: Path) -> str:
        if self._transcriber is None:
            self._transcriber = self._transcriber_factory()
        return self._transcriber.transcribe(path)

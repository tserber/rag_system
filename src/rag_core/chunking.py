"""Plain text chunking with character-based overlap.

Deliberately simple (no tokenizer dependency) so it has zero extra cost.
Swap in a token-aware splitter later if chunk boundaries start cutting
sentences in ways that hurt retrieval quality.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int


def chunk_text(text: str, chunk_size_chars: int = 800, chunk_overlap_chars: int = 120) -> list[Chunk]:
    """Split `text` into overlapping chunks.

    Args:
        text: the raw document text.
        chunk_size_chars: max characters per chunk.
        chunk_overlap_chars: characters shared between consecutive chunks,
            so a sentence spanning a chunk boundary isn't lost entirely.
    """
    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be positive")
    if chunk_overlap_chars < 0 or chunk_overlap_chars >= chunk_size_chars:
        raise ValueError("chunk_overlap_chars must be >= 0 and < chunk_size_chars")

    text = text.strip()
    if not text:
        return []

    step = chunk_size_chars - chunk_overlap_chars
    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + chunk_size_chars, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(text=piece, index=index))
            index += 1
        if end == len(text):
            break
        start += step
    return chunks

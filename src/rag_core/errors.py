"""Custom exceptions so interfaces can tell "a dependency is down" apart from
"there's a bug", and reply/log accordingly instead of leaking a raw
traceback to a Telegram user or an API caller.
"""

from __future__ import annotations


class RagCoreError(Exception):
    """Base class for every error rag_core raises on purpose."""


class VectorStoreUnavailableError(RagCoreError):
    """Qdrant could not be reached, or a request to it failed."""


class EmbeddingError(RagCoreError):
    """The embedding model failed to load or encode text."""


class GenerationUnavailableError(RagCoreError):
    """Ollama (or another generation backend) could not be reached or failed."""

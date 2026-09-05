"""rag_core: framework-agnostic retrieval (and optional generation) engine.

This package must never import anything from `interfaces/` (telegram_bot, api).
It knows nothing about Telegram, FastAPI, or Django. Anything that talks to
those frameworks lives under `interfaces/` and imports *from* rag_core, never
the other way around.
"""

from rag_core.pipeline import RagPipeline, RagResponse, RetrievedChunk

__all__ = ["RagPipeline", "RagResponse", "RetrievedChunk"]

"""Central configuration for rag_core.

All switches described in the README (local vs cloud Qdrant, retrieval-only
vs Ollama generation) are plain environment variables so nothing here is
hardcoded. Copy .env.example to .env and edit it; nothing is read from disk
except through these settings.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QdrantMode(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class GenerationMode(str, Enum):
    RETRIEVAL_ONLY = "retrieval_only"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Qdrant ---
    qdrant_mode: QdrantMode = QdrantMode.LOCAL
    qdrant_collection: str = "rag_documents"

    # local mode
    qdrant_local_host: str = "localhost"
    qdrant_local_port: int = 6333

    # cloud mode (Qdrant Cloud free tier or any managed cluster)
    qdrant_cloud_url: str | None = None
    qdrant_cloud_api_key: str | None = None

    # --- Embeddings ---
    # Any sentence-transformers model name. multilingual-e5-small is a good
    # free default if you expect non-English text; bge-small-en-v1.5 is
    # slightly better for English-only.
    embedding_model: str = "intfloat/multilingual-e5-small"

    # --- Chunking ---
    chunk_size_chars: int = 800
    chunk_overlap_chars: int = 120

    # --- Retrieval ---
    top_k: int = 3

    # --- Generation ---
    generation_mode: GenerationMode = GenerationMode.RETRIEVAL_ONLY
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # --- Telegram (read by interfaces/telegram_bot, not by rag_core itself) ---
    telegram_bot_token: str | None = Field(default=None)


def get_settings() -> Settings:
    """Load settings fresh from the environment/.env file.

    Not cached on purpose: tests and scripts frequently need to override
    environment variables and re-read settings within the same process.
    """
    return Settings()

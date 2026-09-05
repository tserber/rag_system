"""Check whether rag_core's dependencies (Qdrant, and Ollama if enabled) are
actually reachable right now.

Used by every interface (Telegram's /health command, FastAPI's GET /health)
so a user gets a clear "Qdrant isn't reachable right now" instead of a silent
failure, a raw stack trace, or a message that just hangs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from rag_core.config import GenerationMode, QdrantMode, Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class HealthReport:
    services: list[ServiceStatus] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(s.ok for s in self.services)


def check_qdrant(settings: Settings) -> ServiceStatus:
    try:
        from qdrant_client import QdrantClient

        if settings.qdrant_mode == QdrantMode.CLOUD:
            client = QdrantClient(
                url=settings.qdrant_cloud_url, api_key=settings.qdrant_cloud_api_key, timeout=5
            )
        else:
            client = QdrantClient(
                host=settings.qdrant_local_host, port=settings.qdrant_local_port, timeout=5
            )
        client.get_collections()
        return ServiceStatus(name="qdrant", ok=True)
    except Exception as exc:  # broad on purpose: this is a reachability probe, not business logic
        logger.warning("Qdrant health check failed: %s", exc)
        return ServiceStatus(name="qdrant", ok=False, detail=str(exc))


def check_ollama(settings: Settings) -> ServiceStatus:
    try:
        import requests

        response = requests.get(f"{settings.ollama_host.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
        return ServiceStatus(name="ollama", ok=True)
    except Exception as exc:  # broad on purpose, same reason as above
        logger.warning("Ollama health check failed: %s", exc)
        return ServiceStatus(name="ollama", ok=False, detail=str(exc))


def check_health(settings: Settings | None = None) -> HealthReport:
    """Only checks services the current config actually needs: Ollama is
    skipped entirely when GENERATION_MODE=retrieval_only.
    """
    settings = settings or get_settings()
    services = [check_qdrant(settings)]
    if settings.generation_mode == GenerationMode.OLLAMA:
        services.append(check_ollama(settings))
    return HealthReport(services=services)

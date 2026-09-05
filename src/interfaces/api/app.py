"""Minimal FastAPI interface, proving rag_core works outside Telegram too.

This is intentionally small -- a demo of the seam, not a production API
(no auth, no rate limiting). If this project grows a real HTTP API, or a
Django one, it belongs here (or in an equivalent interfaces/django_app),
reusing the exact same RagPipeline.

Run with:
    uvicorn interfaces.api.app:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from rag_core import RagPipeline
from rag_core.config import get_settings
from rag_core.errors import RagCoreError
from rag_core.healthcheck import check_health
from rag_core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="rag_system API")
_pipeline: RagPipeline | None = None


def get_pipeline() -> RagPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RagPipeline()
    return _pipeline


class QueryRequest(BaseModel):
    text: str
    top_k: int | None = None
    sphere: str | None = None
    technology: str | None = None


class ChunkOut(BaseModel):
    text: str
    score: float
    metadata: dict


class QueryResponse(BaseModel):
    query: str
    chunks: list[ChunkOut]
    answer: str | None


class ServiceStatusOut(BaseModel):
    name: str
    ok: bool
    detail: str = ""


class HealthResponse(BaseModel):
    ok: bool
    services: list[ServiceStatusOut]


@app.get("/health", response_model=HealthResponse)
def health(response: Response):
    report = check_health(get_settings())
    if not report.all_ok:
        # 503 so load balancers / uptime checks / `curl -f` see this as down,
        # not just a 200 with a buried "ok": false in the body.
        response.status_code = 503
    return HealthResponse(
        ok=report.all_ok,
        services=[ServiceStatusOut(name=s.name, ok=s.ok, detail=s.detail) for s in report.services],
    )


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = get_pipeline().query(
            request.text, top_k=request.top_k, sphere=request.sphere, technology=request.technology
        )
    except RagCoreError as exc:
        logger.error("Query %r failed: %s", request.text, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error handling query %r", request.text)
        raise HTTPException(status_code=500, detail="Internal error, see server logs.") from exc

    return QueryResponse(
        query=result.query,
        chunks=[ChunkOut(text=c.text, score=c.score, metadata=c.metadata) for c in result.chunks],
        answer=result.answer,
    )

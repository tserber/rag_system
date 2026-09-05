"""Turns a rag_core.RagResponse into a Telegram message string.

Kept separate from main.py so it's trivially unit-testable without spinning
up aiogram or a Telegram connection.
"""

from __future__ import annotations

from rag_core import RagResponse
from rag_core.healthcheck import HealthReport


def format_health(report: HealthReport) -> str:
    if report.all_ok:
        return "All services are up."
    lines = ["Service status:"]
    for service in report.services:
        status = "up" if service.ok else "DOWN"
        lines.append(f"- {service.name}: {status}" + (f" ({service.detail})" if service.detail else ""))
    return "\n".join(lines)


def format_response(response: RagResponse) -> str:
    if not response.chunks:
        return "No matching results found."

    if response.answer:
        lines = [response.answer, "", "Sources:"]
        for i, chunk in enumerate(response.chunks, start=1):
            source = chunk.metadata.get("source", "unknown")
            lines.append(f"{i}. {source} (score {chunk.score:.2f})")
        return "\n".join(lines)

    # Retrieval-only mode: show the top matches directly.
    lines = [f"Top {len(response.chunks)} matches:"]
    for i, chunk in enumerate(response.chunks, start=1):
        source = chunk.metadata.get("source", "unknown")
        snippet = chunk.text if len(chunk.text) <= 500 else chunk.text[:500] + "..."
        lines.append(f"\n{i}. (score {chunk.score:.2f}, {source})\n{snippet}")
    return "\n".join(lines)

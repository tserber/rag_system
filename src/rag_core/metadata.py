"""Structured metadata attached to every indexed chunk.

Every chunk gets, on top of its source file and chunk index:

- `sphere`: the broad domain, e.g. "databases", "backend", "networking".
- `technology`: the specific thing within that domain, e.g. "postgresql",
  "mongodb", "sql", "redis".

This is what makes filtered retrieval possible ("only show me Postgres
chunks", "only databases, not networking") without redesigning storage
later -- the fields exist in every payload from day one, even if a given
document doesn't populate them.

Convention: organize `data/` as `data/<sphere>/<technology>/*.{md,txt}`,
e.g. `data/databases/postgresql/indexing.md`, and sphere/technology are
inferred automatically from the path at ingest time. Files placed directly
in `data/` (no subfolders) get sphere=None, technology=None -- ingestion
still works, you just lose filtering for those files. Override the
inferred values explicitly by constructing ChunkMetadata yourself if the
folder convention doesn't fit a document.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    text: str
    source: str
    chunk_index: int
    sphere: str | None = None
    technology: str | None = None

    def to_payload(self) -> dict:
        return self.model_dump()


def infer_sphere_and_technology(file_path: Path, data_root: Path) -> tuple[str | None, str | None]:
    """Infer (sphere, technology) from a file's position under data_root.

    data/databases/postgresql/notes.md -> ("databases", "postgresql")
    data/networking/dns.md             -> ("networking", None)
    data/notes.md                      -> (None, None)
    """
    try:
        relative_parts = file_path.resolve().relative_to(data_root.resolve()).parts
    except ValueError:
        return None, None

    parts = relative_parts[:-1]  # drop the filename itself
    sphere = parts[0] if len(parts) >= 1 else None
    technology = parts[1] if len(parts) >= 2 else None
    return sphere, technology

"""One place to configure logging so every entrypoint (bot, API, ingest CLI)
sets it up the same way. Call this once, at process start, before anything
else logs.
"""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

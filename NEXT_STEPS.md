# Status

The `transformers` bug documented here previously is resolved. Ingestion
has been run successfully and retrieval has been verified against the new
interview-prep content. This file is now a record of what happened and
what's still worth doing, not a blocker list.

## What got fixed

Every `transformers` 5.x release available in this environment had the
same genuine packaging bug: `nn.Module` referenced in a type annotation in
`transformers/integrations/accelerate.py` with no `import torch.nn as nn`
and no `from __future__ import annotations`, so importing the module raised
`NameError: name 'nn' is not defined` before any model was even touched.
Since `sentence-transformers>=6.0` requires `transformers>=5.0`, the fix
was downgrading both together to a `sentence-transformers<6` /
`transformers<5` pair, which pulled in the proven-stable `transformers`
4.x line instead.

That surfaced a second, unrelated issue: `torch==2.2.2` (the newest version
available here) was built against numpy's 1.x C ABI and throws
`RuntimeError: Numpy is not available` under numpy 2.x. Fixed by capping
`numpy<2.0`, which in turn needed `scipy<1.13` and `scikit-learn<1.5` to
stay mutually compatible (newer scipy/scikit-learn require numpy>=2.0).

All of this is now pinned explicitly in `pyproject.toml`'s `dependencies`,
with comments explaining why each cap exists, so a fresh install doesn't
silently hit the same wall. `requirements-lock.txt` is regenerated from the
now-working environment (`pip freeze`), for a fully reproducible install.

## What got ingested

`python -m rag_core.ingest ./data` -- **144 chunks from 14 files**, covering
all of `data/interview-prep/` (the CSV-derived question bank, the questions
I added myself, and the real interview Q&A pulled from this session's
transcribed recordings). Spot-checked retrieval against
`RagPipeline().query("What is the difference between a list and a tuple?")`
-- top result (score 0.898) was exactly the right chunk.

## Also done this round

`rag_core/ingest.py` was refactored to an OOP strategy pattern, matching
the Protocol-with-swappable-implementations style already used for
`Embedder`/`VectorStore`/`Generator`:
- `rag_core/ingest_strategies.py` -- `IngestStrategy` protocol,
  `TextFileStrategy`, `AudioFileStrategy`. Each strategy owns `can_handle()`
  + `extract_text()` for one source type.
- `Ingester` class in `ingest.py` picks a strategy per file and runs the
  same chunk/embed/upsert pipeline regardless of what produced the text.
  Adding a new source type (PDF, HTML, a URL fetcher) means writing one new
  strategy class, not touching `Ingester`'s control flow.
- The old module-level `ingest_folder()` function still exists as a thin
  wrapper around `Ingester().ingest_folder()`, so the CLI
  (`python -m rag_core.ingest`) and existing callers didn't need to change.
- Covered by `tests/test_ingest_strategies.py` and two new tests in
  `tests/test_ingest.py` proving a custom strategy list actually works and
  that an unclaimed file type is skipped, not an error.

## Worth doing later (not blocking)

- Point `README.md`/`agents.md` at `requirements-lock.txt` with a one-line
  "for a reproducible install, use this instead of `pip install -e .`"
  note -- not done yet, low priority.
- Revisit whether `data/interview-prep/backend-engineering` overlaps enough
  with `core-python`/`databases`/`web-frameworks` to merge -- not a
  retrieval problem, just worth a look if the duplication bothers you.
- If a future `transformers` 5.x release actually fixes the `nn` import,
  the version caps in `pyproject.toml` can be relaxed back up -- the
  comments there explain exactly what to re-test before doing that.

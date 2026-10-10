# Next steps

Where things stand, and what's left before the new interview-prep content
is actually usable. Nothing below has been run yet -- read this before
doing anything, don't just re-run commands blind.

## What's already done (saved, not yet indexed)

- CSV questions ingested into the project's convention:
  `data/interview-prep/{core-python,web-frameworks,databases,architecture}/qa-bank.md`
- Supplementary questions I wrote myself, same folders: `own-questions.md`
- Real Q&A pulled from our earlier interview-transcript work, copied in as:
  `data/interview-prep/{backend-engineering,ai-rag-engineering,coding-challenges,qa-testing,behavioral-leadership,recruiter-process}/real-interview-qa.md`
- `.gitignore` updated so `data/interview-prep/` is actually tracked by git
  (it was being silently excluded by the blanket `data/*` rule before).
- Qdrant is running locally (`docker compose up -d qdrant`).
- `requirements-lock.txt` written at the project root -- `pip freeze` output
  of the current `.venv`, for reference. **It currently includes the known-
  broken `transformers==5.19.0` pin below -- do not treat this file as
  "known good" yet.**

## Blocker: broken `transformers` install

Ingestion fails before it reaches Qdrant -- loading the embedding model
throws `NameError: name 'nn' is not defined` inside
`transformers/integrations/accelerate.py`. This is a real upstream bug in
`transformers==5.19.0` (the latest release pip resolved), not our code.

`sentence-transformers==6.1.0` requires `transformers>=5.0.0,<6.0.0`, so
downgrading to the 4.x line isn't an option without also downgrading
`sentence-transformers`.

### What to try, in order

1. Check if a newer `transformers` patch release has fixed it:
   `pip install -q --upgrade "transformers>=5,<6"` and retry ingest. If a
   point release past 5.19.0 exists by the time this is picked up, this is
   the first thing to try.
2. If no fix is out yet, try a slightly older 5.x patch
   (`pip install -q "transformers==5.18.0"` etc., working backwards) to
   find one that doesn't hit this import bug while still satisfying
   `sentence-transformers`'s `>=5.0.0` floor.
3. If nothing in the 5.x line works, the fallback is downgrading
   `sentence-transformers` itself to a version compatible with
   `transformers<5` (check its own changelog/compatibility table), or
   swapping `EMBEDDING_MODEL` to a model path that works with a known-good
   `sentence-transformers`/`transformers` pair.
4. Once a working combination is found, **pin it explicitly** in
   `pyproject.toml`'s `dependencies` (not just left floating on `>=`), and
   regenerate `requirements-lock.txt` from a clean venv so this doesn't
   silently break again on a fresh install.

## After the embedding model loads

1. Run the actual ingest: `python -m rag_core.ingest ./data`
2. Sanity-check retrieval against a few real questions from the new
   content, e.g. via the Telegram bot or a quick `RagPipeline.query(...)`
   in a REPL -- confirm `sphere`/`technology` metadata looks right and
   answers are actually pulling from the new files.
3. Review the diff (`git status` / `git diff`) -- in particular confirm
   `.gitignore`'s new `!data/interview-prep/**` exception is only picking
   up the intended files, not something unexpected.
4. Commit and push -- only once 1-3 above are actually verified working,
   not before.

## Also worth doing, lower priority

- `requirements-lock.txt` should get documented somewhere (README or
  agents.md) once it reflects a known-good environment -- a one-line
  pointer ("for a reproducible install: `pip install -r requirements-lock.txt`
  instead of `pip install -e .`") is enough, no need for a longer section.
- Consider whether `data/interview-prep/backend-engineering` and
  `data/interview-prep/core-python` / `databases` / `web-frameworks`
  content overlaps enough to merge -- they currently live as separate,
  unrelated folders even though some topics (hashing, REST, ACID) appear
  in both the CSV bank and the real-interview transcripts. Not a problem
  for retrieval, just worth a look if the duplication bothers you later.

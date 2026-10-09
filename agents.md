# agents.md

Instructions for any AI coding agent (or human) working in this repository.

## What this project is

A retrieval system over Qdrant, with a Telegram bot as the current front-end.
Input: a text message. Output: the top-k retrieved chunks from Qdrant, and
optionally an LLM-generated answer synthesized from them (switchable, see
below). Everything runs locally and free by default; AWS is a documented,
not-yet-built, deployment target.

## Hard rule: module boundaries

```
src/
  rag_core/          <- retrieval + generation engine. Framework-agnostic.
    live/            <- audio-stream -> questions (vad_segmenter) and
                        questions -> speculative answers (question_matcher).
                        Still framework-agnostic: no microphone import here.
  interfaces/
    telegram_bot/    <- imports rag_core. Telegram-specific.
    api/             <- imports rag_core. FastAPI-specific.
    live_listener/   <- imports rag_core (incl. rag_core.live). Owns the
                        microphone (sounddevice), same way telegram_bot owns
                        aiogram and api owns FastAPI.
```

`rag_core` must never import `aiogram`, `fastapi`, `django`, or anything else
from `interfaces/`. It must not know a Telegram message or an HTTP request
exists. The only public entry point interfaces are allowed to use is
`rag_core.RagPipeline`.

If you're adding a Django front-end later: create `src/interfaces/django_app/`,
import `RagPipeline` there, and do not touch `rag_core`. If a feature seems to
require breaking this boundary, that's a signal the feature belongs in
`rag_core` as a new capability on `RagPipeline`, not in the interface layer.

## Architecture

```
message/request
      |
      v
interfaces/telegram_bot or interfaces/api   (thin: parse input, call pipeline, format output)
      |
      v
rag_core.RagPipeline.query(text)
      |
      +--> Retriever (embeds query, searches VectorStore)
      |        |
      |        +--> Embedder (SentenceTransformersEmbedder, local, free)
      |        +--> VectorStore (QdrantVectorStore: local Docker or Qdrant Cloud, config-switched)
      |
      (at ingest time, not query time: Transcriber (FasterWhisperTranscriber,
       local, free) turns audio files into text before it reaches Embedder --
       see rag_core/ingest.py and rag_core/transcription.py)
      |
      +--> Generator (NullGenerator: retrieval-only, or OllamaGenerator: local LLM)
      |
      v
RagResponse(query, chunks, answer)
```

`interfaces/live_listener` is a separate, parallel caller of this same
pipeline, not a new path through it:

```
microphone audio
      |
      v
rag_core.live.VadSegmenter          (turns a raw audio stream into utterances)
      |
      v
FasterWhisperTranscriber.transcribe_array()   (same transcriber as file ingestion)
      |
      v
rag_core.live.QuestionMatcher       (fires RagPipeline.query() on partial text,
      |                              surfaces an early answer once stable,
      |                              flags same-theme follow-up questions)
      v
LiveAnswer(question_text, response, is_same_theme_as_previous)
```

Every piece above is a `Protocol`-typed interface with one real implementation
today. Adding a second implementation (e.g. an API-based embedder, a remote
embedder running on a phone, a different vector DB) means writing a new class
with the same method signatures — nothing else changes.

## Config, not code, for switches

All environment-driven behavior lives in `rag_core/config.py:Settings`, backed
by `.env` (copy `.env.example`). Two switches matter most:

- `QDRANT_MODE=local|cloud` — local Docker Qdrant vs. Qdrant Cloud free tier.
- `GENERATION_MODE=retrieval_only|ollama` — return raw top-k chunks, or run
  them through a local Ollama model first.

Never hardcode a host, model name, or API key in code — add a `Settings`
field instead.

## Running things

```bash
pip install -e ".[dev]"
cp .env.example .env

docker compose up qdrant                       # local vector DB
docker compose --profile generation up ollama  # only if GENERATION_MODE=ollama

python -m rag_core.ingest ./data               # index documents from data/
python -m interfaces.telegram_bot.main         # run the bot (needs TELEGRAM_BOT_TOKEN)
uvicorn interfaces.api.app:app --reload        # run the FastAPI demo instead/also
python -m interfaces.live_listener.main        # live mic listening (needs pip install -e ".[live]")

pytest                                         # all tests run offline against fakes
```

## Conventions

- Python 3.11+, type hints everywhere, `from __future__ import annotations` at
  the top of modules that use `|` unions on older-style declarations.
- Dataclasses/Pydantic models for data shapes, not dicts, once a shape is used
  in more than one place.
- Tests for `rag_core` and `interfaces/*` use fakes (see `tests/test_pipeline.py`)
  instead of a live Qdrant/Ollama/model — keep it that way so `pytest` never
  needs network access or a model download. Add an integration test suite
  separately if/when that's needed.
- No em dashes in comments, docstrings, or commit messages.

## Current status / known gaps

- Document-source metadata is filename + `sphere`/`technology`/`kind`
  (`kind` is `"text"` for a plain file, `"audio_transcript"` for a
  transcribed one). If you add PDF/HTML ingestion, follow the same pattern:
  extend the payload in `ingest.py`, not the retriever.
- Ingestion is idempotent: each chunk's Qdrant point ID is `uuid5(fixed
  namespace, f"{source}::{chunk_index}")`, not random, so re-running
  `ingest_folder` on a folder you've already indexed updates existing
  points in place instead of duplicating them (see `_stable_chunk_id` in
  `ingest.py`). One known gap: if editing a file *shrinks* its chunk count,
  the now-unreferenced higher-index chunks from the previous run are
  orphaned in Qdrant rather than deleted -- no reconciliation pass exists
  yet; rebuilding the collection is the current workaround.
- Audio ingestion (`rag_core/transcription.py`, wired into `ingest.py`) needs
  the optional `faster-whisper` dependency (`pip install -e ".[audio]"`) and
  is CPU-only by default; it is not installed as part of the base package so
  machines that never ingest audio don't pay for it.
- Live listening (`rag_core/live/`, `interfaces/live_listener/`) needs the
  optional `[live]` extra (`[audio]` plus `sounddevice`). Voice-activity
  detection is a simple RMS-energy threshold, not a trained VAD model --
  deliberate for v1 (KISS); swapping in webrtcvad/silero-vad later is a
  one-file change to `rag_core/live/vad_segmenter.py`, nothing else in the
  live path needs to know. There's also no two-tier fast/accurate model
  split for partial vs. final transcription yet -- one model (whichever
  `WHISPER_MODEL_SIZE` is configured) handles both; if partial-decode
  latency ever becomes the bottleneck, a smaller dedicated "draft" model for
  `transcribe_array()` calls during on_partial() is the documented upgrade
  path, not something to build preemptively.
- No auth on the FastAPI demo endpoint; it's a proof that `rag_core` is
  reusable outside Telegram, not a production API.
- AWS deployment is intentionally not built yet (see README's "Local vs AWS"
  section for the tradeoffs that led to this).
- The phone-as-a-node ideas (embedding worker, Ollama, always-on relay) are
  documented in the README but not implemented. If picked up, they should
  plug in as a new `Embedder`/`Generator` implementation talking HTTP to the
  phone, not as a special case elsewhere.

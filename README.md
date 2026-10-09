# rag_system

A retrieval system over [Qdrant](https://qdrant.tech/), with a Telegram bot as
the front-end. You send it a message, it returns the top matching chunks from
your indexed documents (and optionally an LLM-generated answer on top of
them). Local and free by default; AWS is a documented, future deployment
option, not something this repo assumes you'll pay for.

See [`agents.md`](./agents.md) for the architecture, module boundaries, and
how-to-run instructions in detail. This file covers the reasoning behind the
choices made.

## Features (read this first)

Everything this system can do, listed up front in one place — for a human
skimming the repo, and in a consistent `name` / `description` / `input` /
`run` shape so an AI coding agent exploring this codebase can discover every
capability without having to read every module first.

| Feature | Description | Input | Run |
|---|---|---|---|
| `ingest_documents` | Chunk, embed, and index `.txt`/`.md` files into Qdrant. | A folder of text files, organized as `data/<sphere>/<technology>/*.md` (sphere/technology are inferred from the path). | `python -m rag_core.ingest ./data` |
| `ingest_audio` | Transcribe audio files to text (locally, via Whisper), then chunk/embed/index exactly like a document — see [Audio transcription](#audio-transcription) below. | Audio files (`.mp3 .wav .m4a .flac .ogg .mp4 .webm`) dropped in the **same** `data/` folder as text files — no separate command needed. | `python -m rag_core.ingest ./data` *(same command — audio files are detected automatically)* |
| `query` (Telegram) | Ask a question in a Telegram chat, get back the top matching chunks (and optionally an LLM-generated answer). | A plain-text message to the bot. | `python -m interfaces.telegram_bot.main` |
| `query` (HTTP API) | Same retrieval/generation pipeline, over a REST endpoint — proves `rag_core` works outside Telegram too. | `POST` with a query string/JSON body. | `uvicorn interfaces.api.app:app --reload` |
| `filtered_retrieval` | Narrow results to a specific `sphere` and/or `technology` instead of searching everything. | `sphere` / `technology` query parameters, matched against each chunk's metadata. | Built into `query` above — pass the filters through the bot/API. |
| `health_check` | Report whether Qdrant (and Ollama, if generation is on) are actually reachable. | None. | See `rag_core.healthcheck` / the bot's health command. |
| `live_listen` | Listen to a microphone continuously, detect each spoken question, and answer it against your indexed documents — with an early answer offered before the question even finishes. See [Live listening](#live-listening) below. | A live microphone feed. | `python -m interfaces.live_listener.main` |

Every row above is one capability of `rag_core.RagPipeline` or its ingestion
CLI — see [`agents.md`](./agents.md) for the full architecture these plug
into, and the module boundaries that keep each one swappable.

## Why local-first, with AWS as a documented option

Running everything on your own machine (Qdrant in Docker, optionally Ollama)
costs nothing recurring, keeps your data local, and lets you iterate as fast
as you can restart a container. The tradeoff: the bot only answers while your
machine is on, there's no public URL without a tunnel (ngrok, Cloudflare
Tunnel, Tailscale Funnel), and you're capped by your machine's RAM when
running an embedding model and an LLM at the same time.

Hosting on AWS (EC2 for the bot/API, Qdrant Cloud or self-hosted Qdrant on
EC2) buys you an always-on, publicly reachable service that doesn't depend on
your laptop being awake, at the cost of real recurring spend and more to
secure (IAM, security groups, secrets). For a personal project, AWS mostly
buys uptime and shareability, not better retrieval quality, so it's kept out
of scope for now. `rag_core`'s `QdrantVectorStore` already supports both
modes (`QDRANT_MODE=local` or `cloud`) so moving is a config change, not a
rewrite.

## Free alternatives used or worth knowing about

| Need | Paid option | Free option used here |
|---|---|---|
| Embeddings | OpenAI/Cohere embeddings API | `sentence-transformers` locally (CPU) |
| Generation | Claude/OpenAI API | Ollama running a local open model |
| Vector DB | Managed Qdrant Cloud (paid tiers) | Local Qdrant in Docker |
| Always-on hosting | AWS EC2 | Oracle Cloud "Always Free" tier, or a Tailscale/Cloudflare tunnel to your own machine |

Qdrant Cloud does have a genuine free tier (1GB RAM / 4GB disk single-node
cluster, no HA/SLA) if you'd rather not run Docker yourself; `QDRANT_MODE=cloud`
in `.env` switches to it. See [Qdrant's pricing page](https://qdrant.tech/pricing/).

## Could the phone be used? (8GB RAM, Snapdragon)

Documented here as options, not built yet:

- **Embedding worker**: run `sentence-transformers` (or a lighter ONNX/ggml
  equivalent) on the phone via Termux, expose it over HTTP, point
  `rag_core`'s `Embedder` at it. Lightweight enough to be genuinely practical.
- **Small local LLM**: Termux + llama.cpp or Ollama-in-Termux can run a
  quantized 2-3B model (Phi-3 mini, Gemma 2 2B, Qwen2.5 3B) comfortably on
  8GB total RAM; a 7-8B model at 4-bit is possible but tight, slow, and hard
  on the battery. Treat it as an experimental second `Generator`, not a
  primary one.
- **Always-on relay**: install Tailscale on the phone so it's a reachable
  endpoint even when your main machine sleeps, without paying for a cloud VM.
- **Hosting Qdrant itself on the phone**: possible via Termux+proot, not
  recommended — phones sleep and throttle in ways a real always-on host
  shouldn't. A Raspberry Pi is the better "free-ish always-on" box if you
  want one.
- **Just using it as the Telegram client**: already free, since Telegram
  works everywhere.

If any of these get built, they should be a new `Embedder` or `Generator`
implementation calling the phone over HTTP, per `agents.md`'s architecture
rules, not a special case elsewhere.

## Why the retrieval/Telegram split

`rag_core` (the retrieval + optional generation engine) has zero knowledge of
Telegram. `interfaces/telegram_bot/` is a thin adapter that calls
`RagPipeline.query()` and formats the result as a Telegram message.
`interfaces/api/` is a small FastAPI demo doing the exact same thing over
HTTP, proving the split actually works. A Django front-end later is the same
pattern: a new `interfaces/django_app/` that imports `RagPipeline` and
nothing else from this project.

## Audio transcription

You can drop audio recordings (interviews, meeting notes, voice memos) into
`data/` right alongside your `.txt`/`.md` files, and they get turned into
searchable, askable knowledge the same way a document does — no separate
pipeline to learn.

### How it works, in plain language

1. **Listening in chunks, not all at once.** The audio is scanned for where
   people are actually speaking (voice activity detection), so silence and
   dead air get skipped instead of wasting time "transcribing" nothing.
2. **Turning sound into text.** Each spoken chunk goes through a local
   speech-recognition model ([Whisper](https://github.com/openai/whisper),
   run via the faster, CPU-friendly
   [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) library) that
   converts the audio into written words — entirely on your own machine, no
   audio ever leaves it and no API key is needed.
3. **Stitching it back together.** The individual chunks of recognized text
   are joined into one plain-text transcript of the whole recording.
4. **Treating it like any other document.** From there, the transcript is
   chunked, embedded, and indexed into Qdrant using the exact same code path
   as a `.md` file — so asking the Telegram bot a question can pull an answer
   from something someone *said* just as easily as from something written.

Chunks that came from audio are tagged `kind: "audio_transcript"` in their
metadata (plain text files are tagged `kind: "text"`), so you can always tell
where a retrieved answer actually came from.

### How to run it

```bash
# 1. Install the extra (one-time) -- this is separate from the base install
#    so you only need it if you actually plan to ingest audio.
pip install -e ".[audio]"

# 2. Drop audio files into data/, same as you would a .md file, e.g.:
#    data/interviews/backend-call.mp3

# 3. Run the normal ingest command -- audio files are picked up automatically,
#    alongside any .txt/.md files already there.
python -m rag_core.ingest ./data
```

That's it — no flags, no second command. The console will log
`Transcribing <file> ...` for each audio file as it works through them, then
report the total chunks indexed, same as for text files.

**Good to know before you run it on a long recording:** transcription runs
on your CPU by default and takes real time — roughly comparable to the
length of the recording itself for the default model, sometimes faster
thanks to the silence-skipping step above. A one-hour recording is a
"start it, go do something else, come back" job, not an instant one. If you
want to trade some speed for accuracy (or vice versa), two settings in
`.env` control that:

```bash
WHISPER_MODEL_SIZE=small   # tiny < base < small (default) < medium < large-v3
WHISPER_DEVICE=cpu         # set to "cuda" if you have an NVIDIA GPU available
```

Bigger models are more accurate (especially on technical vocabulary, accents,
or background noise) but slower; smaller models are faster but can miss
words or mis-transcribe jargon. `small` is a reasonable default to start
with.

## Live listening

Instead of transcribing a recording after the fact, `interfaces.live_listener`
listens to your microphone continuously and answers each question against
your indexed documents as it's asked — useful for having your own notes on
tap *during* an interview, not just for prepping before one.

```bash
pip install -e ".[live]"
python -m interfaces.live_listener.main
```

How it stays fast and keeps running, in short (see `rag_core/live/` for the
actual implementation):

- **Early answers, not just final ones.** While a question is still being
  spoken, the growing partial transcript is searched repeatedly in the
  background. Once the same top result holds steady across a few partials
  in a row, that answer is shown immediately — usually before the question
  even finishes, rather than waiting for a pause. A final search runs once
  the question is confirmed complete, which normally just confirms what was
  already shown.
- **Keeps listening through a multi-hour interview.** Audio capture and the
  transcribe-and-answer loop are decoupled, and any error (a device hiccup,
  a bad transcription) restarts the listening session instead of crashing
  the process — you don't have to babysit it.
- **Same-theme questions are flagged, not repeated.** If two consecutive
  questions retrieve the same top source, the second is flagged as a
  restatement/follow-up of the first rather than presented as an unrelated
  new answer.
- **Nothing here is reimplemented.** Transcription reuses the exact same
  `FasterWhisperTranscriber` as batch audio ingestion (just fed an in-memory
  buffer instead of a file), and retrieval reuses `RagPipeline` unchanged —
  the only genuinely new code is turning a raw audio stream into questions
  (`rag_core/live/vad_segmenter.py`) and deciding when a retrieved answer is
  confident enough to show (`rag_core/live/question_matcher.py`).

Voice-activity detection here is intentionally simple (an energy/RMS
threshold, not a trained model) — good enough to find pauses between
questions without adding a new dependency; swapping in a more accurate VAD
later is a one-file change, nothing else in the live-listening path needs
to know.

## Quickstart

```bash
pip install -e ".[dev]"
cp .env.example .env
docker compose up qdrant

python -m rag_core.ingest ./data       # put some .txt/.md files in data/ first
python -m interfaces.telegram_bot.main # needs TELEGRAM_BOT_TOKEN in .env

pytest
```

Want to index audio recordings too (interviews, voice notes), not just text?
See [Audio transcription](#audio-transcription) above — it's one extra
install (`pip install -e ".[audio]"`) and then the same `ingest` command
above picks up audio files automatically.

To switch on LLM-generated answers instead of raw chunks:

```bash
docker compose --profile generation up ollama
ollama pull llama3.1:8b   # or whichever OLLAMA_MODEL you set in .env
# set GENERATION_MODE=ollama in .env, restart the bot
```

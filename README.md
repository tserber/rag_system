# rag_system

A retrieval system over [Qdrant](https://qdrant.tech/), with a Telegram bot as
the front-end. You send it a message, it returns the top matching chunks from
your indexed documents (and optionally an LLM-generated answer on top of
them). Local and free by default; AWS is a documented, future deployment
option, not something this repo assumes you'll pay for.

See [`agents.md`](./agents.md) for the architecture, module boundaries, and
how-to-run instructions in detail. This file covers the reasoning behind the
choices made.

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

## Quickstart

```bash
pip install -e ".[dev]"
cp .env.example .env
docker compose up qdrant

python -m rag_core.ingest ./data       # put some .txt/.md files in data/ first
python -m interfaces.telegram_bot.main # needs TELEGRAM_BOT_TOKEN in .env

pytest
```

To switch on LLM-generated answers instead of raw chunks:

```bash
docker compose --profile generation up ollama
ollama pull llama3.1:8b   # or whichever OLLAMA_MODEL you set in .env
# set GENERATION_MODE=ollama in .env, restart the bot
```

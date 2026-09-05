"""Telegram front-end: message in, retrieved chunks (or generated answer) out.

This file must stay thin. Anything about how retrieval or generation works
belongs in rag_core, not here -- if you find yourself writing Qdrant or
embedding logic in this file, it's in the wrong place.

Run with:
    python -m interfaces.telegram_bot.main
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from interfaces.telegram_bot.formatting import format_health, format_response
from rag_core import RagPipeline
from rag_core.config import get_settings
from rag_core.errors import RagCoreError
from rag_core.healthcheck import check_health
from rag_core.logging_config import configure_logging

logger = logging.getLogger(__name__)

dispatcher = Dispatcher()
pipeline: RagPipeline | None = None  # built in run() once settings/token are validated


@dispatcher.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "Send me a question and I'll search the knowledge base and reply with the top matches.\n"
        "Use /health to check whether Qdrant (and Ollama, if enabled) are reachable."
    )


@dispatcher.message(Command("health"))
async def handle_health(message: Message) -> None:
    settings = get_settings()
    report = await asyncio.to_thread(check_health, settings)
    await message.answer(format_health(report))


@dispatcher.message()
async def handle_query(message: Message) -> None:
    assert pipeline is not None
    query_text = (message.text or "").strip()
    if not query_text:
        await message.answer("Send a text message to search for.")
        return

    await message.chat.do("typing")
    try:
        response = await asyncio.to_thread(pipeline.query, query_text)
    except RagCoreError as exc:
        # A known, named dependency failure (Qdrant/Ollama down, embedding
        # model failed to load, ...). Log the detail, tell the user plainly,
        # don't leak internals or crash the bot over one bad request.
        logger.error("Query %r failed: %s", query_text, exc)
        await message.answer(
            "One of the services this bot depends on isn't available right now "
            f"({exc}). Try /health to see which one, and try again once it's back up."
        )
        return
    except Exception:
        # Anything unexpected: log the full traceback for debugging, but
        # still give the user a plain answer instead of letting aiogram's
        # own error handling (or silence) take over.
        logger.exception("Unexpected error handling query %r", query_text)
        await message.answer("Something went wrong handling that request. It's been logged.")
        return

    await message.answer(format_response(response))


async def run() -> None:
    global pipeline
    configure_logging()
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    pipeline = RagPipeline(settings=settings)
    bot = Bot(token=settings.telegram_bot_token)

    startup_report = check_health(settings)
    if not startup_report.all_ok:
        logger.warning("Starting up with a dependency already down: %s", format_health(startup_report))
    logger.info("Starting Telegram bot (generation_mode=%s)", settings.generation_mode)

    await dispatcher.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

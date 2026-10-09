"""Live interview-question listening, over a microphone instead of Telegram
or HTTP. Same pattern as the other interfaces (see agents.md): this file
owns the microphone and the console; everything about turning audio into an
answer lives in rag_core (RagPipeline, FasterWhisperTranscriber,
rag_core.live.VadSegmenter, rag_core.live.QuestionMatcher).

Usage:
    pip install -e ".[live]"   # sounddevice, on top of the [audio] extra
    python -m interfaces.live_listener.main

What it does, end to end:

1. Opens the default microphone at 16kHz mono (faster-whisper's native
   rate -- capturing at that rate directly means no resampling step).
2. Feeds 30ms frames into VadSegmenter, which tracks when someone is
   speaking vs. silent.
3. While someone is mid-question, periodically transcribes the
   in-progress buffer (a partial) and feeds it to QuestionMatcher, which
   fires a retrieval lookup and only surfaces an early answer once the
   result has been stable for a few partials in a row -- this is the
   "answer before the question finishes" behavior.
4. Once VadSegmenter detects the question has ended (a pause), the full
   utterance is transcribed and queried one more time as the confirmed,
   authoritative answer.
5. The whole capture+listen loop is wrapped so a single error (a device
   hiccup, a transcription failure) logs and restarts the stream rather
   than killing the process -- "unstoppable" in the practical sense of
   "keeps listening through a multi-hour interview without needing a
   human to notice it died and restart it."
"""

from __future__ import annotations

import logging
import queue
import time

import numpy as np

from rag_core.config import get_settings
from rag_core.errors import TranscriptionError
from rag_core.live.question_matcher import LiveAnswer, QuestionMatcher
from rag_core.live.vad_segmenter import VadSegmenter
from rag_core.logging_config import configure_logging
from rag_core.pipeline import RagPipeline
from rag_core.transcription import FasterWhisperTranscriber

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # faster-whisper's native rate; capturing at this rate skips resampling
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000
PARTIAL_DECODE_INTERVAL_S = 0.7  # how often to re-transcribe the in-progress question


def run_forever() -> None:
    """Entry point: listens until interrupted (Ctrl+C), restarting the
    audio stream on any error instead of exiting."""
    configure_logging()
    settings = get_settings()

    transcriber = FasterWhisperTranscriber(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    matcher = QuestionMatcher(RagPipeline(settings), stability_streak=settings.live_stability_streak)
    silence_frames = max(1, settings.live_silence_ms // FRAME_MS)

    logger.info("Live listener starting (Ctrl+C to stop)...")
    while True:
        try:
            _listen_session(transcriber, matcher, silence_frames)
        except KeyboardInterrupt:
            logger.info("Live listener stopped.")
            return
        except Exception:  # broad on purpose: this is the top-level "keep listening no matter what" loop
            logger.exception("Live listener session crashed; restarting in 2s")
            time.sleep(2)


def _listen_session(transcriber: FasterWhisperTranscriber, matcher: QuestionMatcher, silence_frames: int) -> None:
    import sounddevice as sd

    segmenter = VadSegmenter(silence_frames_to_end_utterance=silence_frames)
    frame_queue: queue.Queue[np.ndarray] = queue.Queue()

    def on_audio(indata, frames, time_info, status) -> None:
        if status:
            logger.warning("Audio input status: %s", status)
        frame_queue.put(indata[:, 0].copy())

    last_partial_decode = 0.0
    with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES, channels=1, dtype="float32", callback=on_audio):
        while True:
            frame = frame_queue.get()
            utterance = segmenter.push(frame)

            if utterance is not None:
                _handle_final(transcriber, matcher, utterance)
                last_partial_decode = 0.0
                continue

            now = time.monotonic()
            if now - last_partial_decode < PARTIAL_DECODE_INTERVAL_S:
                continue
            partial_audio = segmenter.current_partial()
            if partial_audio is None:
                continue
            last_partial_decode = now
            _handle_partial(transcriber, matcher, partial_audio)


def _handle_partial(transcriber: FasterWhisperTranscriber, matcher: QuestionMatcher, audio: np.ndarray) -> None:
    try:
        partial_text = transcriber.transcribe_array(audio)
    except TranscriptionError:
        return  # too little audio to say anything useful yet -- not an error, just not ready
    answer = matcher.on_partial(partial_text)
    if answer is not None:
        _print_answer(answer, early=True)


def _handle_final(transcriber: FasterWhisperTranscriber, matcher: QuestionMatcher, audio: np.ndarray) -> None:
    try:
        final_text = transcriber.transcribe_array(audio)
    except TranscriptionError:
        logger.warning("Could not transcribe a completed utterance; skipping")
        return
    answer = matcher.on_final(final_text)
    _print_answer(answer, early=False)


def _print_answer(answer: LiveAnswer, early: bool) -> None:
    tag = "~early~" if early else "CONFIRMED"
    theme_note = " (same theme as previous)" if answer.is_same_theme_as_previous else ""
    print(f"\n[{tag}] Q: {answer.question_text}{theme_note}")
    response = answer.response
    if response.answer:
        print(f"A: {response.answer}")
    for i, chunk in enumerate(response.chunks[:3], start=1):
        source = chunk.metadata.get("source", "unknown")
        print(f"  {i}. ({chunk.score:.2f}) {source}")


if __name__ == "__main__":
    run_forever()

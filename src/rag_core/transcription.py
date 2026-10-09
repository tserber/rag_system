"""Speech-to-text backends, so audio files (interview recordings, voice
notes, meeting audio) can be ingested the same way .txt/.md files are.

Only one implementation today (local faster-whisper, free, CPU-friendly) but
it's behind an interface so a remote/API-based transcriber (e.g. a hosted
Whisper endpoint) can be added later without touching ingest.py.

How it works, end to end:

1. The audio file (mp3/wav/m4a/flac/ogg) is decoded to a mono 16kHz waveform
   by the `av` library (bundled with faster-whisper) -- no system `ffmpeg`
   install required, unlike the original openai-whisper.
2. The waveform is split into chunks using voice activity detection (VAD),
   so silence is skipped rather than transcribed -- this is most of why
   transcription finishes faster than "audio length" would suggest.
3. Each voiced chunk is converted to a log-Mel spectrogram and run through
   Whisper's encoder/decoder (a transformer model) to produce text tokens,
   generated one at a time conditioned on the audio and the tokens already
   produced.
4. Segments are joined back together, in order, into one plain-text
   transcript -- this module deliberately returns plain text (no
   timestamps), since that's what ingest.py chunks and embeds; keep using
   the timestamped version if you need a human-readable transcript, this is
   for feeding the retrieval pipeline.

Failures (missing `faster-whisper` dependency, unreadable/corrupt audio,
model failing to load) are logged and re-raised as TranscriptionError so
ingest.py can catch one known type, same as every other rag_core backend.

`transcribe()` (a file on disk) and `transcribe_array()` (raw audio already
in memory, used by rag_core.live for microphone input) share the same model
loading and error handling via `_run()` -- the only thing that differs
between batch file ingestion and live listening is where the audio comes
from, not how it's turned into text.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from rag_core.errors import TranscriptionError

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

# Extensions routed through transcription instead of being read as plain
# text. `av` (faster-whisper's audio decoder) handles all of these without
# needing a system ffmpeg install.
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".webm"}


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> str:
        """Return the full plain-text transcript of an audio file."""
        ...


class FasterWhisperTranscriber:
    """Local, free, CPU-friendly transcriber using faster-whisper.

    The model is loaded lazily on first use so importing this module (or
    rag_core generally) never triggers a model download, and never requires
    the optional `faster-whisper` dependency unless transcription is
    actually used.
    """

    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8") -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)
            return self._model
        except ImportError as exc:
            raise TranscriptionError(
                "faster-whisper is not installed. Run: pip install -e \".[audio]\""
            ) from exc
        except Exception as exc:
            logger.exception("Failed to load Whisper model '%s'", self._model_size)
            raise TranscriptionError(f"Could not load Whisper model '{self._model_size}': {exc}") from exc

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe a complete audio file on disk (batch ingestion)."""
        return self._run(str(audio_path), context=str(audio_path))

    def transcribe_array(self, audio: np.ndarray) -> str:
        """Transcribe raw mono float32 PCM audio already in memory, sampled
        at 16kHz (faster-whisper's native rate) -- the live-listening path,
        where there is no file on disk, just a buffer captured from a
        microphone. Same model, same loading, same error handling as
        transcribe(); only the source differs.
        """
        return self._run(audio, context="<live audio>")

    def _run(self, source: str | np.ndarray, context: str) -> str:
        try:
            model = self._load()
            segments, _info = model.transcribe(source, beam_size=5, vad_filter=True)
            text = " ".join(segment.text.strip() for segment in segments).strip()
        except TranscriptionError:
            raise
        except Exception as exc:
            logger.exception("Transcribing %s failed", context)
            raise TranscriptionError(f"Failed to transcribe '{context}': {exc}") from exc

        if not text:
            raise TranscriptionError(f"No speech detected in '{context}'")
        return text

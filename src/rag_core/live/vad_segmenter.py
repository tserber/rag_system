"""Splits a stream of raw audio frames into utterances using simple
energy-based voice activity detection (VAD).

Deliberately simple (an RMS threshold, not a trained VAD model) -- KISS over
accuracy for a first version. Swapping in a more accurate VAD (webrtcvad,
silero-vad) later means replacing this one class; nothing else in
rag_core.live or interfaces/live_listener changes, since callers only see
push() in, completed utterance out.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class VadSegmenter:
    silence_rms_threshold: float = 0.01
    # How many consecutive silent frames end an utterance. At the default
    # 30ms frame size (see interfaces/live_listener), 20 frames is ~600ms of
    # silence -- long enough to not cut off a mid-sentence breath, short
    # enough to feel responsive once the question actually ends.
    silence_frames_to_end_utterance: int = 20

    _in_speech: bool = field(default=False, init=False)
    _silence_run: int = field(default=0, init=False)
    _buffer: list[np.ndarray] = field(default_factory=list, init=False)

    def push(self, frame: np.ndarray) -> np.ndarray | None:
        """Feed one frame of mono float32 audio (range -1..1).

        Returns the completed utterance (concatenated float32 audio) once
        enough silence follows speech; otherwise None, meaning "keep
        listening, nothing to transcribe yet."
        """
        is_voiced = _rms(frame) >= self.silence_rms_threshold

        if is_voiced:
            self._in_speech = True
            self._silence_run = 0
            self._buffer.append(frame)
            return None

        if not self._in_speech:
            return None  # silence before any speech started -- ignore it

        self._silence_run += 1
        self._buffer.append(frame)  # keep trailing silence, sounds more natural if ever played back
        if self._silence_run < self.silence_frames_to_end_utterance:
            return None

        return self._flush()

    def current_partial(self) -> np.ndarray | None:
        """The in-progress utterance so far, without ending it -- used to
        feed speculative partial transcription while the question is still
        being spoken. None if nothing is currently buffered."""
        if not self._buffer:
            return None
        return np.concatenate(self._buffer)

    def _flush(self) -> np.ndarray:
        utterance = np.concatenate(self._buffer) if self._buffer else np.array([], dtype=np.float32)
        self._buffer = []
        self._in_speech = False
        self._silence_run = 0
        return utterance


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame))))

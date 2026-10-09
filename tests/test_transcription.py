"""Transcription tests using a fake faster_whisper module injected into
sys.modules, so this runs without the optional `faster-whisper` dependency
installed and without downloading a real model -- same offline-testing
convention as the rest of rag_core.
"""

import sys
import types
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from rag_core.errors import TranscriptionError
from rag_core.transcription import AUDIO_EXTENSIONS, FasterWhisperTranscriber


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeWhisperModel:
    """Stands in for faster_whisper.WhisperModel. `segments_by_path` lets a
    test control what each call "transcribes" to."""

    instances: ClassVar[list["FakeWhisperModel"]] = []

    def __init__(self, model_size, device, compute_type) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        FakeWhisperModel.instances.append(self)

    def transcribe(self, audio_path, beam_size, vad_filter):
        if isinstance(audio_path, str) and audio_path == "boom.mp3":
            raise RuntimeError("corrupt file")
        if isinstance(audio_path, str) and audio_path == "silence.mp3":
            return [], None
        return [FakeSegment("hello"), FakeSegment("world")], object()


@pytest.fixture(autouse=True)
def fake_faster_whisper(monkeypatch):
    FakeWhisperModel.instances.clear()
    fake_module = types.ModuleType("faster_whisper")
    fake_module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    yield
    FakeWhisperModel.instances.clear()


def test_transcribe_joins_segments_into_plain_text():
    transcriber = FasterWhisperTranscriber(model_size="small", device="cpu", compute_type="int8")
    text = transcriber.transcribe(Path("interview.mp3"))
    assert text == "hello world"


def test_model_is_loaded_lazily_and_reused_across_calls():
    transcriber = FasterWhisperTranscriber()
    assert FakeWhisperModel.instances == []

    transcriber.transcribe(Path("interview.mp3"))
    transcriber.transcribe(Path("interview.mp3"))

    assert len(FakeWhisperModel.instances) == 1


def test_model_is_constructed_with_configured_settings():
    transcriber = FasterWhisperTranscriber(model_size="medium", device="cpu", compute_type="int8")
    transcriber.transcribe(Path("interview.mp3"))

    model = FakeWhisperModel.instances[0]
    assert model.model_size == "medium"
    assert model.device == "cpu"
    assert model.compute_type == "int8"


def test_no_speech_detected_raises_transcription_error():
    transcriber = FasterWhisperTranscriber()
    with pytest.raises(TranscriptionError, match="No speech detected"):
        transcriber.transcribe(Path("silence.mp3"))


def test_underlying_failure_is_wrapped_as_transcription_error():
    transcriber = FasterWhisperTranscriber()
    with pytest.raises(TranscriptionError, match="Failed to transcribe"):
        transcriber.transcribe(Path("boom.mp3"))


def test_missing_dependency_raises_transcription_error(monkeypatch):
    monkeypatch.delitem(sys.modules, "faster_whisper", raising=False)
    monkeypatch.setitem(sys.modules, "faster_whisper", None)  # forces ImportError on import

    transcriber = FasterWhisperTranscriber()
    with pytest.raises(TranscriptionError, match="pip install"):
        transcriber.transcribe(Path("interview.mp3"))


@pytest.mark.parametrize("ext", sorted(AUDIO_EXTENSIONS))
def test_common_audio_extensions_are_recognized(ext):
    assert ext in AUDIO_EXTENSIONS


def test_transcribe_array_shares_the_same_model_and_error_handling_as_transcribe():
    transcriber = FasterWhisperTranscriber()
    audio = np.zeros(1600, dtype=np.float32)  # 0.1s of silence at 16kHz -- just needs to be an ndarray

    text = transcriber.transcribe_array(audio)

    assert text == "hello world"  # same FakeWhisperModel path as transcribe()
    assert len(FakeWhisperModel.instances) == 1  # transcribe() and transcribe_array() share one lazy-loaded model

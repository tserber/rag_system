"""IngestStrategy tests -- pure logic, no fakes needed for TextFileStrategy;
AudioFileStrategy is tested via a fake transcriber factory so this stays
offline, same convention as the rest of rag_core."""

from __future__ import annotations

from pathlib import Path

from rag_core.ingest_strategies import AudioFileStrategy, TextFileStrategy


def test_text_file_strategy_handles_txt_and_md():
    strategy = TextFileStrategy()
    assert strategy.can_handle(Path("notes.md")) is True
    assert strategy.can_handle(Path("notes.txt")) is True
    assert strategy.can_handle(Path("notes.MD")) is True  # case-insensitive


def test_text_file_strategy_rejects_other_extensions():
    strategy = TextFileStrategy()
    assert strategy.can_handle(Path("recording.mp3")) is False
    assert strategy.can_handle(Path("image.png")) is False


def test_text_file_strategy_reads_file_content(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("hello from a text file")

    strategy = TextFileStrategy()
    assert strategy.extract_text(path) == "hello from a text file"


def test_text_file_strategy_has_text_kind():
    assert TextFileStrategy().kind == "text"


def test_audio_file_strategy_handles_known_audio_extensions():
    strategy = AudioFileStrategy(transcriber_factory=lambda: None)
    assert strategy.can_handle(Path("interview.mp3")) is True
    assert strategy.can_handle(Path("interview.wav")) is True
    assert strategy.can_handle(Path("notes.md")) is False


def test_audio_file_strategy_has_audio_transcript_kind():
    assert AudioFileStrategy(transcriber_factory=lambda: None).kind == "audio_transcript"


class FakeTranscriber:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def transcribe(self, path: Path) -> str:
        self.calls.append(path)
        return f"transcribed: {path.name}"


def test_audio_file_strategy_builds_transcriber_lazily():
    built = []

    def factory():
        built.append(1)
        return FakeTranscriber()

    strategy = AudioFileStrategy(transcriber_factory=factory)
    assert built == []  # not built just from constructing the strategy

    strategy.extract_text(Path("interview.mp3"))
    assert built == [1]


def test_audio_file_strategy_reuses_the_same_transcriber_across_calls():
    instances = []

    def factory():
        t = FakeTranscriber()
        instances.append(t)
        return t

    strategy = AudioFileStrategy(transcriber_factory=factory)
    strategy.extract_text(Path("a.mp3"))
    strategy.extract_text(Path("b.mp3"))

    assert len(instances) == 1  # same transcriber instance, not rebuilt per file


def test_audio_file_strategy_delegates_to_transcriber():
    strategy = AudioFileStrategy(transcriber_factory=FakeTranscriber)
    text = strategy.extract_text(Path("interview.mp3"))
    assert text == "transcribed: interview.mp3"

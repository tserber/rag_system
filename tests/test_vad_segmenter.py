import numpy as np

from rag_core.live.vad_segmenter import VadSegmenter

LOUD = np.full(10, 0.2, dtype=np.float32)  # rms 0.2, above the default 0.01 threshold
QUIET = np.zeros(10, dtype=np.float32)  # rms 0.0, below the threshold


def make_segmenter(silence_frames: int = 3) -> VadSegmenter:
    return VadSegmenter(silence_rms_threshold=0.01, silence_frames_to_end_utterance=silence_frames)


def test_silence_before_any_speech_is_ignored():
    segmenter = make_segmenter()
    assert segmenter.push(QUIET) is None
    assert segmenter.push(QUIET) is None
    assert segmenter.current_partial() is None


def test_speech_does_not_flush_until_silence_follows():
    segmenter = make_segmenter()
    assert segmenter.push(LOUD) is None
    assert segmenter.push(LOUD) is None
    partial = segmenter.current_partial()
    assert partial is not None
    assert partial.shape[0] == LOUD.shape[0] * 2


def test_utterance_flushes_after_enough_trailing_silence():
    segmenter = make_segmenter(silence_frames=3)
    segmenter.push(LOUD)
    segmenter.push(LOUD)
    assert segmenter.push(QUIET) is None  # 1st silent frame, not enough yet
    assert segmenter.push(QUIET) is None  # 2nd
    utterance = segmenter.push(QUIET)  # 3rd -- reaches silence_frames_to_end_utterance
    assert utterance is not None
    # 2 loud frames + 3 trailing silent frames were all kept
    assert utterance.shape[0] == LOUD.shape[0] * 2 + QUIET.shape[0] * 3


def test_state_resets_after_flush_for_the_next_utterance():
    segmenter = make_segmenter(silence_frames=1)
    segmenter.push(LOUD)
    segmenter.push(QUIET)  # flushes (silence_frames=1)
    assert segmenter.current_partial() is None

    # A second utterance should work the same way, not be affected by the first
    assert segmenter.push(LOUD) is None
    second = segmenter.push(QUIET)
    assert second is not None
    assert second.shape[0] == LOUD.shape[0] + QUIET.shape[0]


def test_brief_silence_mid_question_does_not_end_the_utterance():
    segmenter = make_segmenter(silence_frames=5)
    segmenter.push(LOUD)
    segmenter.push(QUIET)  # a short breath -- below silence_frames_to_end_utterance
    segmenter.push(QUIET)
    resumed = segmenter.push(LOUD)
    assert resumed is None  # still mid-utterance, not flushed
    partial = segmenter.current_partial()
    assert partial.shape[0] == LOUD.shape[0] * 2 + QUIET.shape[0] * 2

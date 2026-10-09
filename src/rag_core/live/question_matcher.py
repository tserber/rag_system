"""Speculative retrieval for live question-answering.

The idea: don't wait for an interviewer to finish a whole question before
searching. Fire a RagPipeline.query() on the growing partial transcript as
it arrives; once the top retrieved source holds steady across a few
consecutive partials, surface that as an early answer -- it's usually
right well before the question finishes. A final, authoritative query runs
once the question is confirmed complete (see vad_segmenter), which is
normally just a confirmation of what on_partial already found.

This also gives same-question detection almost for free: if two consecutive
*final* questions retrieve the same top source, they're almost certainly a
restatement/refinement of the same question, not a new topic -- useful for
an interface deciding whether to replace the previous answer on screen
instead of appending a new one.

Only depends on RagPipeline, same as every other interface in this project
(see agents.md's module-boundary rule) -- QuestionMatcher itself doesn't
know it's being fed by a microphone.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_core.pipeline import RagPipeline, RagResponse


@dataclass(frozen=True)
class LiveAnswer:
    question_text: str
    response: RagResponse
    is_same_theme_as_previous: bool


class QuestionMatcher:
    def __init__(self, pipeline: RagPipeline, stability_streak: int = 2) -> None:
        """stability_streak: how many consecutive partials must agree on the
        top source before on_partial() surfaces an early answer. Lower is
        faster but flickerier; higher is slower but steadier."""
        self._pipeline = pipeline
        self._stability_streak = stability_streak
        self._streak_source: str | None = None
        self._streak_count = 0
        self._last_final_source: str | None = None

    def on_partial(self, partial_text: str) -> LiveAnswer | None:
        """Call with the growing partial transcript of the question still
        being spoken. Returns an early answer only once the top result has
        held steady for `stability_streak` partials in a row, so the caller
        doesn't flash a different guess on every single update."""
        if not partial_text.strip():
            return None

        response = self._pipeline.query(partial_text)
        top_source = _top_source(response)

        if top_source is not None and top_source == self._streak_source:
            self._streak_count += 1
        else:
            self._streak_source = top_source
            self._streak_count = 1

        if self._streak_count < self._stability_streak:
            return None
        return self._build_answer(partial_text, response)

    def on_final(self, final_text: str) -> LiveAnswer:
        """Call once the question is fully spoken (VadSegmenter returned a
        completed utterance and it was transcribed). Always returns an
        answer, and resets partial-tracking state for the next question."""
        response = self._pipeline.query(final_text)
        answer = self._build_answer(final_text, response)
        self._streak_source = None
        self._streak_count = 0
        self._last_final_source = _top_source(response)
        return answer

    def _build_answer(self, question_text: str, response: RagResponse) -> LiveAnswer:
        same_theme = _top_source(response) is not None and _top_source(response) == self._last_final_source
        return LiveAnswer(question_text=question_text, response=response, is_same_theme_as_previous=same_theme)


def _top_source(response: RagResponse) -> str | None:
    if not response.chunks:
        return None
    return response.chunks[0].metadata.get("source")

from rag_core.live.question_matcher import QuestionMatcher
from rag_core.pipeline import RagResponse, RetrievedChunk


class FakePipeline:
    """Returns responses from a fixed queue, one per query() call, so a test
    can script exactly what each successive partial/final lookup finds --
    same fakes-over-a-live-model approach as test_pipeline.py."""

    def __init__(self, responses: list[RagResponse]) -> None:
        self._responses = list(responses)
        self.queries: list[str] = []

    def query(self, text: str, **kwargs) -> RagResponse:
        self.queries.append(text)
        return self._responses.pop(0)


def response_with_source(query: str, source: str) -> RagResponse:
    return RagResponse(
        query=query,
        chunks=[RetrievedChunk(text="...", score=0.9, metadata={"source": source})],
        answer=None,
    )


def empty_response(query: str) -> RagResponse:
    return RagResponse(query=query, chunks=[], answer=None)


def test_on_partial_withholds_answer_until_stability_streak_reached():
    pipeline = FakePipeline(
        [
            response_with_source("diff", "docs/a.md"),
            response_with_source("difference between", "docs/a.md"),
        ]
    )
    matcher = QuestionMatcher(pipeline, stability_streak=2)

    assert matcher.on_partial("diff") is None  # streak = 1, not enough yet
    answer = matcher.on_partial("difference between")  # same top source, streak = 2
    assert answer is not None
    assert answer.question_text == "difference between"


def test_on_partial_resets_streak_when_top_source_changes():
    pipeline = FakePipeline(
        [
            response_with_source("q1", "docs/a.md"),
            response_with_source("q2", "docs/b.md"),  # source changed -- streak resets
            response_with_source("q3", "docs/b.md"),  # now 2 in a row on b.md
        ]
    )
    matcher = QuestionMatcher(pipeline, stability_streak=2)

    assert matcher.on_partial("q1") is None
    assert matcher.on_partial("q2") is None  # source changed, streak back to 1
    answer = matcher.on_partial("q3")
    assert answer is not None


def test_on_partial_ignores_blank_text():
    matcher = QuestionMatcher(FakePipeline([]), stability_streak=1)
    assert matcher.on_partial("   ") is None


def test_on_final_always_returns_an_answer_and_resets_partial_state():
    pipeline = FakePipeline(
        [
            response_with_source("partial", "docs/a.md"),
            response_with_source("full question?", "docs/a.md"),
        ]
    )
    matcher = QuestionMatcher(pipeline, stability_streak=5)  # streak high enough that on_partial won't fire alone

    assert matcher.on_partial("partial") is None
    final_answer = matcher.on_final("full question?")
    assert final_answer.question_text == "full question?"
    assert final_answer.is_same_theme_as_previous is False  # nothing finalized before this


def test_same_theme_detection_across_consecutive_final_questions():
    pipeline = FakePipeline(
        [
            response_with_source("what is postgres mvcc?", "docs/postgres.md"),
            response_with_source("and how does that compare to locking?", "docs/postgres.md"),
            response_with_source("tell me about docker networking", "docs/docker.md"),
        ]
    )
    matcher = QuestionMatcher(pipeline)

    first = matcher.on_final("what is postgres mvcc?")
    assert first.is_same_theme_as_previous is False

    second = matcher.on_final("and how does that compare to locking?")
    assert second.is_same_theme_as_previous is True  # same top source as the previous final answer

    third = matcher.on_final("tell me about docker networking")
    assert third.is_same_theme_as_previous is False  # topic genuinely changed


def test_on_final_with_no_retrieved_chunks_is_not_same_theme():
    pipeline = FakePipeline([empty_response("q1"), empty_response("q2")])
    matcher = QuestionMatcher(pipeline)

    matcher.on_final("q1")
    second = matcher.on_final("q2")
    assert second.is_same_theme_as_previous is False

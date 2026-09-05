from interfaces.telegram_bot.formatting import format_response
from rag_core.pipeline import RagResponse, RetrievedChunk


def test_no_chunks_message():
    response = RagResponse(query="q", chunks=[], answer=None)
    assert format_response(response) == "No matching results found."


def test_retrieval_only_lists_top_matches():
    response = RagResponse(
        query="q",
        chunks=[RetrievedChunk(text="Warsaw is the capital.", score=0.9, metadata={"source": "a.md"})],
        answer=None,
    )
    out = format_response(response)
    assert "Top 1 matches" in out
    assert "Warsaw is the capital." in out
    assert "a.md" in out


def test_generated_answer_includes_sources():
    response = RagResponse(
        query="q",
        chunks=[RetrievedChunk(text="Warsaw is the capital.", score=0.9, metadata={"source": "a.md"})],
        answer="Warsaw is the capital of Poland.",
    )
    out = format_response(response)
    assert out.startswith("Warsaw is the capital of Poland.")
    assert "Sources:" in out
    assert "a.md" in out

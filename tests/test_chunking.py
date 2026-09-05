from rag_core.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_returns_single_chunk():
    chunks = chunk_text("hello world", chunk_size_chars=800, chunk_overlap_chars=120)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].index == 0


def test_long_text_overlaps_between_chunks():
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size_chars=400, chunk_overlap_chars=100)
    assert len(chunks) > 1
    # consecutive chunks share `chunk_overlap_chars` of content
    assert chunks[0].text[-100:] == chunks[1].text[:100]


def test_rejects_invalid_overlap():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size_chars=100, chunk_overlap_chars=100)

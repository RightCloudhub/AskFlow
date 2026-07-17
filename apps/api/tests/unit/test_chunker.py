from app.services.knowledge.chunker.chunker import chunk_text


def test_chunk_overlap():
    text = "a" * 1200
    chunks = chunk_text(text, size=500, overlap=50)
    assert len(chunks) >= 2
    assert all(len(c) <= 500 for c in chunks)


def test_empty():
    assert chunk_text("") == []

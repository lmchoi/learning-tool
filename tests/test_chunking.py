from core.ingestion.chunker import chunk_document


def test_empty_document_returns_no_chunks() -> None:
    assert chunk_document("") == []


def test_single_paragraph_returns_one_chunk() -> None:
    text = "This is a single paragraph with some content."
    chunks = chunk_document(text)
    assert chunks == [text]


def test_multiple_paragraphs_returns_multiple_chunks() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_document(text)
    assert len(chunks) == 3


def test_chunks_contain_original_content() -> None:
    text = "First paragraph.\n\nSecond paragraph."
    chunks = chunk_document(text)
    assert chunks[0] == "First paragraph."
    assert chunks[1] == "Second paragraph."


def test_whitespace_only_paragraphs_are_excluded() -> None:
    text = "First paragraph.\n\n   \n\nSecond paragraph."
    chunks = chunk_document(text)
    assert len(chunks) == 2


def test_leading_and_trailing_whitespace_stripped() -> None:
    text = "  First paragraph.  \n\n  Second paragraph.  "
    chunks = chunk_document(text)
    assert chunks[0] == "First paragraph."
    assert chunks[1] == "Second paragraph."

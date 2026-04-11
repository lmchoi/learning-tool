def chunk_document(text: str) -> list[str]:
    """Split a document into chunks at paragraph boundaries."""
    if not text.strip():
        return []
    return [s for chunk in text.split("\n\n") if (s := chunk.strip())]

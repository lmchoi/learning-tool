def chunk_document(text: str) -> list[str]:
    """Split a document into chunks at paragraph boundaries."""
    if not text.strip():
        return []
    return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]

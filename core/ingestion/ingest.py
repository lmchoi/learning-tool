from pathlib import Path

from core.ingestion.chunker import chunk_document
from core.ingestion.embedder import Embedder
from core.ingestion.store import ChunkStore


def ingest(context: str, paths: list[Path], embedder: Embedder, store: ChunkStore) -> None:
    """Chunk, embed, and store documents for a given context."""
    all_chunks: list[str] = []

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        all_chunks.extend(chunk_document(path.read_text()))

    embeddings = embedder.embed(all_chunks)
    store.save(context, all_chunks, embeddings)

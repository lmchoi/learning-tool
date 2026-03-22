from pathlib import Path

import pypdf

from core.ingestion.chunker import chunk_document
from core.ingestion.embedder import Embedder
from core.ingestion.store import ChunkStore


def _read_file(path: Path) -> str:
    if path.suffix == ".pdf":
        reader = pypdf.PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text()


def ingest(context: str, paths: list[Path], embedder: Embedder, store: ChunkStore) -> None:
    """Chunk, embed, and store documents for a given context."""
    all_chunks: list[str] = []

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        all_chunks.extend(chunk_document(_read_file(path)))

    embeddings = embedder.embed(all_chunks)
    store.save(context, all_chunks, embeddings)

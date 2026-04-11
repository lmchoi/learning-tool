import logging
from pathlib import Path

import pypdf

from learning_tool.core.ingestion.chunker import chunk_document
from learning_tool.core.ingestion.embedder import Embedder
from learning_tool.core.ingestion.store import ChunkStore

logger = logging.getLogger(__name__)


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
            logger.error("source file not found: %s", path)
            raise FileNotFoundError(f"Source file not found: {path}")
        logger.debug("reading %s", path)
        file_chunks = chunk_document(_read_file(path))
        logger.debug("%s → %d chunk(s)", path.name, len(file_chunks))
        all_chunks.extend(file_chunks)

    logger.info("context=%s files=%d total_chunks=%d", context, len(paths), len(all_chunks))
    logger.debug("embedding %d chunks", len(all_chunks))
    embeddings = embedder.embed(all_chunks)
    store.save(context, all_chunks, embeddings)
    logger.info("saved %d chunks for context=%s", len(all_chunks), context)

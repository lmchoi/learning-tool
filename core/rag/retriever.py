import logging

from core.ingestion.embedder import Embedder
from core.ingestion.store import ChunkStore
from core.rag.similarity import top_k

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, store: ChunkStore, embedder: Embedder) -> None:
        self._store = store
        self._embedder = embedder

    def retrieve(self, context: str, query: str, k: int) -> list[tuple[str, float]]:
        """Return top-k (chunk, score) pairs for a query against a stored context."""
        chunks, embeddings = self._store.load(context)
        query_embedding = self._embedder.embed([query])[0]
        results = top_k(query_embedding, embeddings, chunks, k)
        logger.debug(
            "retrieve context=%s query=%r k=%d scores=%s",
            context,
            query,
            k,
            [round(score, 3) for _, score in results],
        )
        return results

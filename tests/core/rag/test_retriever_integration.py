from pathlib import Path

import pytest

from learning_tool.core.ingestion.embedder import SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore
from learning_tool.core.rag.retriever import Retriever


@pytest.mark.slow
def test_real_query_returns_semantically_relevant_chunk(tmp_path: Path) -> None:
    chunks = [
        "Python asyncio uses an event loop to run coroutines concurrently on a single thread.",
        "French cuisine is known for its rich sauces, fine pastries, and regional diversity.",
        "Cardiac surgery requires precise technique, sterile conditions, and bypass.",
    ]

    embedder = SentenceTransformerEmbedder()
    store = ChunkStore(tmp_path)
    store.save("ctx", chunks, embedder.embed(chunks))

    retriever = Retriever(store=store, embedder=embedder)
    results = retriever.retrieve(context="ctx", query="how does Python handle concurrency", k=1)

    top_chunk, _ = results[0]
    assert "asyncio" in top_chunk

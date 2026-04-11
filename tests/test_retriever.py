from pathlib import Path

import pytest

from learning_tool.core.ingestion.embedder import FakeEmbedder
from learning_tool.core.ingestion.store import ChunkStore
from learning_tool.core.rag.retriever import Retriever


def _store_with_chunks(tmp_path: Path, chunks: list[str], embedder: FakeEmbedder) -> ChunkStore:
    store = ChunkStore(tmp_path)
    store.save("ctx", chunks, embedder.embed(chunks))
    return store


def test_retriever_returns_k_results(tmp_path: Path) -> None:
    embedder = FakeEmbedder(dim=16)
    chunks = ["alpha", "beta", "gamma", "delta"]
    store = _store_with_chunks(tmp_path, chunks, embedder)
    retriever = Retriever(store=store, embedder=embedder)

    results = retriever.retrieve(context="ctx", query="alpha", k=2)

    assert len(results) == 2


def test_retriever_returns_chunks_and_scores(tmp_path: Path) -> None:
    embedder = FakeEmbedder(dim=16)
    chunks = ["alpha", "beta"]
    store = _store_with_chunks(tmp_path, chunks, embedder)
    retriever = Retriever(store=store, embedder=embedder)

    results = retriever.retrieve(context="ctx", query="alpha", k=2)

    assert all(isinstance(text, str) for text, _ in results)
    assert all(isinstance(score, float) for _, score in results)


def test_retriever_scores_are_descending(tmp_path: Path) -> None:
    embedder = FakeEmbedder(dim=16)
    chunks = ["alpha", "beta", "gamma"]
    store = _store_with_chunks(tmp_path, chunks, embedder)
    retriever = Retriever(store=store, embedder=embedder)

    results = retriever.retrieve(context="ctx", query="alpha", k=3)
    scores = [score for _, score in results]

    assert scores == sorted(scores, reverse=True)


def test_retriever_k_larger_than_corpus_returns_all(tmp_path: Path) -> None:
    embedder = FakeEmbedder(dim=16)
    chunks = ["only", "two"]
    store = _store_with_chunks(tmp_path, chunks, embedder)
    retriever = Retriever(store=store, embedder=embedder)

    results = retriever.retrieve(context="ctx", query="something", k=100)

    assert len(results) == 2


def test_retriever_exact_match_ranks_first(tmp_path: Path) -> None:
    # FakeEmbedder is deterministic — same text produces same vector.
    # The query vector for "alpha" is identical to the stored "alpha" embedding,
    # so cosine similarity = 1.0, guaranteed top rank.
    embedder = FakeEmbedder(dim=16)
    chunks = ["alpha", "beta", "gamma"]
    store = _store_with_chunks(tmp_path, chunks, embedder)
    retriever = Retriever(store=store, embedder=embedder)

    results = retriever.retrieve(context="ctx", query="alpha", k=3)

    assert results[0][0] == "alpha"
    assert results[0][1] == pytest.approx(1.0)

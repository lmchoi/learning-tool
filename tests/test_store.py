from pathlib import Path

import numpy as np
import pytest

from core.ingestion.store import ChunkStore, ContextStore
from core.models import ContextMetadata


def test_context_store_round_trip(tmp_path: Path) -> None:
    store = ContextStore(tmp_path)
    metadata = ContextMetadata(
        goal="Preparing for a senior ML engineer interview.",
        focus_areas=["LLM evaluation", "Python async", "ML system design"],
    )

    store.save_context("my-context", metadata)
    loaded = store.load_context("my-context")

    assert loaded is not None
    assert loaded.goal == metadata.goal
    assert loaded.focus_areas == metadata.focus_areas


def test_context_store_overwrites_existing(tmp_path: Path) -> None:
    store = ContextStore(tmp_path)
    old = ContextMetadata(goal="old goal", focus_areas=["old area"])
    new = ContextMetadata(goal="new goal", focus_areas=["new area"])

    store.save_context("ctx", old)
    store.save_context("ctx", new)
    loaded = store.load_context("ctx")

    assert loaded is not None
    assert loaded.goal == "new goal"


def test_context_store_returns_none_when_missing(tmp_path: Path) -> None:
    store = ContextStore(tmp_path)
    assert store.load_context("does-not-exist") is None


def test_store_and_load_round_trip(tmp_path: Path) -> None:
    store = ChunkStore(tmp_path)
    chunks = ["first chunk", "second chunk"]
    embeddings = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)

    store.save("my-context", chunks, embeddings)
    loaded_chunks, loaded_embeddings = store.load("my-context")

    assert loaded_chunks == chunks
    np.testing.assert_array_equal(loaded_embeddings, embeddings)


def test_save_overwrites_existing(tmp_path: Path) -> None:
    store = ChunkStore(tmp_path)
    embeddings = np.array([[0.1, 0.2]], dtype=np.float32)

    store.save("ctx", ["old chunk"], embeddings)
    store.save("ctx", ["new chunk"], embeddings)
    chunks, _ = store.load("ctx")

    assert chunks == ["new chunk"]


def test_load_missing_context_raises(tmp_path: Path) -> None:
    store = ChunkStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load("does-not-exist")


def test_different_contexts_are_isolated(tmp_path: Path) -> None:
    store = ChunkStore(tmp_path)
    emb = np.array([[0.1, 0.2]], dtype=np.float32)

    store.save("ctx-a", ["chunk a"], emb)
    store.save("ctx-b", ["chunk b"], emb)

    chunks_a, _ = store.load("ctx-a")
    chunks_b, _ = store.load("ctx-b")

    assert chunks_a == ["chunk a"]
    assert chunks_b == ["chunk b"]

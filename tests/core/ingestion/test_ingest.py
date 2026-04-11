from pathlib import Path

import pytest

from learning_tool.core.ingestion.embedder import FakeEmbedder
from learning_tool.core.ingestion.ingest import ingest
from learning_tool.core.ingestion.store import ChunkStore


def test_ingest_stores_chunks_and_embeddings(tmp_path: Path) -> None:
    doc = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    source_file = tmp_path / "doc.md"
    source_file.write_text(doc)

    store = ChunkStore(tmp_path / "store")
    embedder = FakeEmbedder(dim=8)

    ingest(context="test", paths=[source_file], embedder=embedder, store=store)

    chunks, embeddings = store.load("test")
    assert len(chunks) == 3
    assert embeddings.shape == (3, 8)


def test_ingest_multiple_files(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("Doc A paragraph.")
    (tmp_path / "b.md").write_text("Doc B paragraph.")

    store = ChunkStore(tmp_path / "store")
    embedder = FakeEmbedder(dim=8)

    ingest(
        context="test",
        paths=[tmp_path / "a.md", tmp_path / "b.md"],
        embedder=embedder,
        store=store,
    )

    chunks, embeddings = store.load("test")
    assert len(chunks) == 2
    assert embeddings.shape == (2, 8)


def test_ingest_missing_file_raises(tmp_path: Path) -> None:
    store = ChunkStore(tmp_path / "store")
    embedder = FakeEmbedder(dim=8)

    with pytest.raises(FileNotFoundError):
        ingest(
            context="test",
            paths=[tmp_path / "missing.md"],
            embedder=embedder,
            store=store,
        )


def test_reingest_overwrites(tmp_path: Path) -> None:
    source_file = tmp_path / "doc.md"
    source_file.write_text("Only paragraph.")

    store = ChunkStore(tmp_path / "store")
    embedder = FakeEmbedder(dim=8)

    ingest(context="test", paths=[source_file], embedder=embedder, store=store)
    ingest(context="test", paths=[source_file], embedder=embedder, store=store)

    chunks, _ = store.load("test")
    assert len(chunks) == 1

from pathlib import Path

import pytest

from core.ingestion.embedder import SentenceTransformerEmbedder
from core.ingestion.ingest import ingest
from core.ingestion.store import ChunkStore


@pytest.mark.slow
def test_real_embedder_ingest_and_load(tmp_path: Path) -> None:
    doc = """# Introduction

This is the first section of the document.

## Background

This section covers background information about the topic.

## Conclusion

This is the final section with concluding thoughts."""

    source_file = tmp_path / "doc.md"
    source_file.write_text(doc)

    store = ChunkStore(tmp_path / "store")
    embedder = SentenceTransformerEmbedder()

    ingest(context="test", paths=[source_file], embedder=embedder, store=store)

    chunks, embeddings = store.load("test")

    assert len(chunks) == 6
    assert embeddings.shape == (6, 384)
    assert embeddings.dtype.name == "float32"

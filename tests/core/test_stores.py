from pathlib import Path

from learning_tool.core.context_import.draft_store import DraftStore
from learning_tool.core.ingestion.embedder import FakeEmbedder, SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore, ContextStore
from learning_tool.core.rag.retriever import Retriever
from learning_tool.core.stores import create_stores


def test_create_stores(tmp_path: Path) -> None:
    """Factory should return correctly initialized store objects."""
    stores = create_stores(tmp_path)

    assert isinstance(stores.chunk_store, ChunkStore)
    assert isinstance(stores.embedder, SentenceTransformerEmbedder)
    assert isinstance(stores.retriever, Retriever)
    assert isinstance(stores.context_store, ContextStore)
    assert isinstance(stores.draft_store, DraftStore)

    assert stores.chunk_store.base_dir == tmp_path
    assert stores.context_store.base_dir == tmp_path
    assert stores.draft_store.drafts_dir == tmp_path / "drafts"
    assert stores.store_dir == tmp_path


def test_create_stores_with_custom_embedder(tmp_path: Path) -> None:
    """Factory should use provided embedder instead of default."""
    fake_embedder = FakeEmbedder(dim=8)
    stores = create_stores(tmp_path, embedder=fake_embedder)

    assert stores.embedder is fake_embedder

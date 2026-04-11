from pathlib import Path
from typing import NamedTuple

from learning_tool.core.context_import.draft_store import DraftStore
from learning_tool.core.ingestion.embedder import Embedder, SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore, ContextStore
from learning_tool.core.rag.retriever import Retriever


class Stores(NamedTuple):
    """
    Shared stores and objects for RAG and context management.

    Exposes 'embedder' because it's required directly by ingestion tasks,
    even though it's also an implementation detail of Retriever.

    'store_dir' is included as a convenience for creating context-scoped
    stores (like QuestionBankStore and SessionStore) on demand.
    """

    chunk_store: ChunkStore
    embedder: Embedder
    retriever: Retriever
    context_store: ContextStore
    draft_store: DraftStore
    store_dir: Path


def create_stores(store_dir: Path, embedder: Embedder | None = None) -> Stores:
    """
    Create and initialize shared RAG and context stores.

    If no embedder is provided, a SentenceTransformerEmbedder is created.
    """
    if embedder is None:
        embedder = SentenceTransformerEmbedder()

    chunk_store = ChunkStore(store_dir)
    retriever = Retriever(store=chunk_store, embedder=embedder)
    context_store = ContextStore(store_dir)
    draft_store = DraftStore(store_dir)

    return Stores(
        chunk_store=chunk_store,
        embedder=embedder,
        retriever=retriever,
        context_store=context_store,
        draft_store=draft_store,
        store_dir=store_dir,
    )

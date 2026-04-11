from pathlib import Path
from typing import NamedTuple

from learning_tool.core.context_import.draft_store import DraftStore
from learning_tool.core.ingestion.embedder import SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore, ContextStore
from learning_tool.core.rag.retriever import Retriever


class Stores(NamedTuple):
    chunk_store: ChunkStore
    embedder: SentenceTransformerEmbedder
    retriever: Retriever
    context_store: ContextStore
    draft_store: DraftStore


def create_stores(store_dir: Path) -> Stores:
    """Create and initialize RAG and context stores."""
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
    )

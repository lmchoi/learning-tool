import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


class ChunkStore:
    """Persists chunks and their embeddings to disk, keyed by context name."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save(self, context: str, chunks: list[str], embeddings: NDArray[np.float32]) -> None:
        ctx_dir = self.base_dir / context
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "chunks.json").write_text(json.dumps(chunks))
        np.save(ctx_dir / "embeddings.npy", embeddings)

    def load(self, context: str) -> tuple[list[str], NDArray[np.float32]]:
        ctx_dir = self.base_dir / context
        chunks_file = ctx_dir / "chunks.json"
        embeddings_file = ctx_dir / "embeddings.npy"

        if not chunks_file.exists() or not embeddings_file.exists():
            raise FileNotFoundError(f"No store found for context '{context}'")

        chunks: list[str] = json.loads(chunks_file.read_text())
        embeddings = np.load(embeddings_file)
        return chunks, embeddings

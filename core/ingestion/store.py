import json
from pathlib import Path

import numpy as np
import yaml
from numpy.typing import NDArray

from core.models import ContextMetadata


class ContextStore:
    """Persists context metadata (goal + focus areas) to context.yaml, keyed by context name."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save_context(self, context: str, metadata: ContextMetadata) -> None:
        ctx_dir = self.base_dir / context
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "context.yaml").write_text(
            yaml.dump(metadata.model_dump(), default_flow_style=False)
        )

    def load_context(self, context: str) -> ContextMetadata:
        ctx_file = self.base_dir / context / "context.yaml"
        if not ctx_file.exists():
            raise FileNotFoundError(f"No context found for '{context}'")
        data = yaml.safe_load(ctx_file.read_text())
        return ContextMetadata(**data)


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

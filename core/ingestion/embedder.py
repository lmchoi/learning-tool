from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class Embedder(Protocol):
    def embed(self, chunks: list[str]) -> NDArray[np.float32]:
        """Embed a list of text chunks, returning a (len(chunks), dim) array."""
        ...


class FakeEmbedder:
    """Deterministic embedder for testing. Returns normalised vectors from a hash seed."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, chunks: list[str]) -> NDArray[np.float32]:
        if not chunks:
            return np.zeros((0, self.dim), dtype=np.float32)

        vectors = []
        for chunk in chunks:
            rng = np.random.default_rng(seed=hash(chunk) % (2**32))
            vec = rng.standard_normal(self.dim).astype(np.float32)
            vec /= np.linalg.norm(vec)
            vectors.append(vec)

        return np.array(vectors, dtype=np.float32)


class SentenceTransformerEmbedder:
    """Real embedder using sentence-transformers. Use in integration tests and production."""

    MODEL = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.MODEL)

    def embed(self, chunks: list[str]) -> NDArray[np.float32]:
        if not chunks:
            return np.zeros((0, 384), dtype=np.float32)
        result: NDArray[np.float32] = self._model.encode(
            chunks, normalize_embeddings=True, convert_to_numpy=True
        )
        return result

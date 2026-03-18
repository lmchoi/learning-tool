import numpy as np
from numpy.typing import NDArray


def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    """Cosine similarity between two 1-D vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def top_k(
    query: NDArray[np.float32],
    embeddings: NDArray[np.float32],
    chunks: list[str],
    k: int,
) -> list[tuple[str, float]]:
    """Return up to k (chunk, score) pairs ranked by cosine similarity."""
    scores = embeddings @ query / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query))
    k = min(k, len(chunks))
    top_indices = np.argsort(scores)[::-1][:k]
    return [(chunks[i], float(scores[i])) for i in top_indices]

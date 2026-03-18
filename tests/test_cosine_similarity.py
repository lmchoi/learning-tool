import numpy as np
import pytest

from core.rag.similarity import cosine_similarity, top_k


def test_identical_vectors_score_one() -> None:
    vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_orthogonal_vectors_score_zero() -> None:
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_opposite_vectors_score_minus_one() -> None:
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([-1.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, b) == pytest.approx(-1.0)


def test_top_k_returns_k_highest_in_order() -> None:
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],  # score 1.0  — rank 1
            [0.0, 1.0, 0.0],  # score 0.0  — rank 3
            [0.7, 0.7, 0.0],  # score ~0.7 — rank 2
        ],
        dtype=np.float32,
    )
    chunks = ["best", "worst", "middle"]

    results = top_k(query, embeddings, chunks, k=2)

    assert [text for text, _ in results] == ["best", "middle"]


def test_top_k_scores_are_descending() -> None:
    query = np.array([1.0, 0.0], dtype=np.float32)
    embeddings = np.array([[0.6, 0.8], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    chunks = ["a", "b", "c"]

    results = top_k(query, embeddings, chunks, k=3)
    scores = [score for _, score in results]

    assert scores == sorted(scores, reverse=True)


def test_top_k_larger_than_corpus_returns_all() -> None:
    query = np.array([1.0, 0.0], dtype=np.float32)
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    chunks = ["a", "b"]

    results = top_k(query, embeddings, chunks, k=10)

    assert len(results) == 2

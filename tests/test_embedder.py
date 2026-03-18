import numpy as np

from core.ingestion.embedder import Embedder, FakeEmbedder


def test_fake_embedder_returns_array_per_chunk() -> None:
    embedder: Embedder = FakeEmbedder(dim=8)
    chunks = ["first chunk", "second chunk", "third chunk"]
    embeddings = embedder.embed(chunks)
    assert embeddings.shape == (3, 8)


def test_fake_embedder_returns_normalised_vectors() -> None:
    embedder: Embedder = FakeEmbedder(dim=16)
    embeddings = embedder.embed(["some text"])
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-6)


def test_fake_embedder_same_input_returns_same_output() -> None:
    embedder: Embedder = FakeEmbedder(dim=8)
    a = embedder.embed(["hello world"])
    b = embedder.embed(["hello world"])
    np.testing.assert_array_equal(a, b)


def test_fake_embedder_empty_input_returns_empty_array() -> None:
    embedder: Embedder = FakeEmbedder(dim=8)
    embeddings = embedder.embed([])
    assert embeddings.shape == (0, 8)

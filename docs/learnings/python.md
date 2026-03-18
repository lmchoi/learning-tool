# Python learnings

## Structural typing with Protocol

`Protocol` defines an interface by shape, not inheritance. Any class with matching
method signatures satisfies it — no need to inherit or register.

```python
class Embedder(Protocol):
    def embed(self, chunks: list[str]) -> NDArray[np.float32]: ...
```

`FakeEmbedder` and `SentenceTransformerEmbedder` never reference `Embedder` — they
just match its shape. mypy verifies this statically.

Contrast with ABCs: ABCs require explicit inheritance (`class Foo(Base)`).
Protocols work with any existing class, including third-party ones you can't modify.

---

## Lazy imports for expensive dependencies

Import inside `__init__` to defer the cost until the object is actually created:

```python
class SentenceTransformerEmbedder:
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # only loaded here
        self._model = SentenceTransformer(self.MODEL)
```

Tests that import the module don't pay the model load cost unless they instantiate
the class. Useful for any heavy dependency (ML models, DB connections, etc).

---

## Pre-commit mypy and project dependencies

`mirrors-mypy` runs in an isolated virtualenv — it doesn't see your project's deps.
You'd have to maintain `additional_dependencies` manually and keep it in sync.

Better: run mypy through `uv run` using `language: system`:

```yaml
- repo: local
  hooks:
    - id: mypy
      name: mypy
      entry: uv run mypy .
      language: system
      types: [python]
      pass_filenames: false
```

`language: system` uses whatever is in PATH — your uv venv. Always in sync,
no duplication.

---

## pytest marks for slow tests

Mark tests that hit real models or external services:

```python
@pytest.mark.slow
def test_real_embedder(...): ...
```

Configure in `pyproject.toml` to skip by default:

```toml
[tool.pytest.ini_options]
addopts = "--import-mode=importlib -m 'not slow'"
markers = ["slow: requires real model, run with -m slow"]
```

Run slow tests explicitly: `uv run pytest -m slow`

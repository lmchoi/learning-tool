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

---

## Walrus operator (:=) to avoid calling a function twice

When filtering and transforming in a list comprehension, you sometimes call the same
function in both the condition and the output expression. The walrus operator assigns
and evaluates in one step, avoiding the double call:

```python
# calls strip() twice per item
[chunk.strip() for chunk in items if chunk.strip()]

# calls strip() once — := assigns the result to s, which is reused in the output
[s for chunk in items if (s := chunk.strip())]
```

The assignment `s := chunk.strip()` evaluates to the stripped string. An empty string
is falsy, so whitespace-only items are filtered out, and `s` in the output expression
reuses the already-computed value.

---

## str.format_map() is single-pass — substituted values are never re-evaluated

`str.format_map(values)` scans the template once, replaces each `{placeholder}` with
the corresponding value from the dict, and returns the result. It never looks at the
substituted values again.

```python
template = "Hello {name}, your input was: {material}"
material = "Call func with {key: value}"  # contains braces

result = template.format_map({"name": "Alice", "material": material})
# → "Hello Alice, your input was: Call func with {key: value}"
# The {key: value} in `material` is NOT interpreted as a placeholder.
```

This means passing user-controlled content (e.g. RAG chunks, user goals) as values is
safe — Python never does a second pass over what was substituted.

The only real failure mode is a `{placeholder}` in the **template itself** that isn't
in the dict — a developer error (typo or missing key), caught immediately at test time.

Contrast with recursive template engines (e.g. PHP double-evaluation) where the output
of one substitution becomes input to another pass. Python's `str.format_map` is not
that — it's closer to a named find-and-replace over a fixed set of slots.

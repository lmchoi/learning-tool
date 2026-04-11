# Convention — Code style

## Grouping in large functions

When a function has multiple initialization steps or logical sections (especially 5+ lines), separate each group with a blank line to improve readability.

Example:
```python
# storage setup
store_dir = STORE_DIR
embedder = SentenceTransformerEmbedder()
store = ChunkStore(store_dir)

# rag components
app.state.retriever = Retriever(store=store, embedder=embedder)
app.state.context_store = ContextStore(store_dir)

# api clients
app.state.anthropic = AsyncAnthropic()
app.state.gemini = genai.Client()
```

This makes the code's structure scannable at a glance. Add a comment only if the group's purpose isn't obvious from the code.

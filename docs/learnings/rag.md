# RAG learnings

## Document chunking

Before embedding, documents need to be split into chunks — pieces small enough to
embed meaningfully and retrieve at query time.

**Why not embed the whole document?** Embedding a large document produces one vector
that averages over everything. A query about one specific topic won't retrieve it
reliably. Smaller, focused chunks embed more precisely.

**Paragraph splitting vs fixed token windows:**

```python
chunks = [s for chunk in text.split("\n\n") if (s := chunk.strip())]
```

Splitting at `\n\n` (blank lines) respects the document's natural structure —
paragraphs and sections are already semantically coherent units. Fixed token windows
(e.g. every 512 tokens) are simpler to implement but cut across ideas arbitrarily.

**Trade-off:** Paragraph chunks vary in size. A one-sentence paragraph is a valid
chunk; so is a ten-sentence one. For well-structured markdown this works well.
For dense prose without clear breaks, fixed windows or overlap strategies may do better.

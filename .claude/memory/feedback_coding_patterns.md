---
name: Preferred coding patterns
description: Python idioms and patterns the user wants applied in this codebase
type: feedback
---

## Walrus operator (:=) in list comprehensions

When filtering and transforming in a list comprehension where the same function is called in both the condition and the output, use the walrus operator to call it once:

```python
# avoid
[chunk.strip() for chunk in items if chunk.strip()]

# prefer
[s for chunk in items if (s := chunk.strip())]
```

# Convention — Engineering principles

## Don't add it until there's a reason to

Don't build for hypothetical future requirements. If something isn't needed right
now, don't add it. This applies to:

- Dependencies — add them when writing the code that needs them, not upfront
- Abstractions — three similar lines of code is better than a premature abstraction
- Infrastructure — don't add a vector store, a cache, or a queue until the simpler
  approach has proven insufficient
- Features — don't add configurability, fallbacks, or error handling for scenarios
  that can't happen yet

The cost of adding something later is usually lower than the cost of carrying
something unnecessary the whole way through.

## Exception: hard-to-reverse architectural decisions

This principle doesn't apply when a decision is difficult to undo or would require
restructuring large parts of the system later. In those cases, think it through
upfront even if the full complexity isn't needed yet.

Ask: *if we don't do this now and need it later, how much does it cost to add?*

- Low cost to add later → don't add it yet
- High cost to add later → worth designing for now (e.g. keeping core domain-agnostic)

## Exception: learning is the goal

This is also a learning project. Sometimes the more complex approach is the right
one not because it's needed, but because understanding it is the point.

When the simpler approach would skip a concept worth understanding deeply — do it
the harder way deliberately. Build numpy RAG before ChromaDB. Write the chunking
logic before abstracting it. The goal is to know what the abstraction is replacing.

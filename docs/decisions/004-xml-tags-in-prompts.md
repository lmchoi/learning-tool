# ADR 004 — Use XML tags to structure prompts

## Status
Accepted

## Context
Prompts sent to Claude mix several types of content: instructions, retrieved context
chunks, and learner profile data. Without clear delimiters, Claude may misinterpret
where one section ends and another begins — especially as prompts grow more complex
(e.g. when evaluation context and question history are added).

## Decision
Structure all prompts with XML tags to separate content types:

```
<context>
...retrieved chunks...
</context>

<instructions>
...what Claude should do...
</instructions>
```

## Why XML tags
Anthropic's own prompt engineering documentation states:

> "XML tags help Claude parse complex prompts unambiguously, especially when your
> prompt mixes instructions, context, examples, and variable inputs. Wrapping each
> type of content in its own tag (e.g. `<instructions>`, `<context>`, `<input>`)
> reduces misinterpretation."

Source: https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/use-xml-tags

Claude is trained to treat XML-tagged content as structured input. This reduces
ambiguity and makes prompt structure explicit and inspectable — useful when
debugging retrieval quality via the CLI.

## Trade-offs
- Slightly more verbose prompts
- Tags need to be consistent across prompt builders (question, evaluation, follow-up)

## Revisit if
Anthropic's guidance changes, or if a different structuring approach proves more
effective for this specific use case.

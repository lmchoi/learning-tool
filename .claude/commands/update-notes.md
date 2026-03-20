Review the current conversation and update learning notes and the learner profile to reflect anything new that was covered.

## Steps

1. List the files in `docs/learnings/` and `contexts/user/`
2. Review the conversation for topics that were explained, discussed, or clarified
3. For each topic found:
   - If a matching file exists in `docs/learnings/`, update it with any new concepts or examples from this conversation
   - If a matching profile exists in `contexts/user/`, update it — move items out of Gaps if understanding improved, add new gaps if something new was explained
   - If no matching file exists, propose a new file name and ask the user to confirm before creating it
4. Use Obsidian `[[wikilink]]` syntax when cross-referencing between notes (e.g. a RAG note referencing `[[python]]` async concepts)
5. Only update what actually changed in this conversation — don't rewrite entries that weren't touched

## File conventions

- `docs/learnings/<topic>.md` — reference notes, "here's how X works", with code examples
- `contexts/user/<topic>.md` — learner profile, "here's what I know/don't know", drives question difficulty

## Existing files (check these first, don't assume)

- `docs/learnings/` — reference notes per topic
- `contexts/user/` — learner profiles per topic

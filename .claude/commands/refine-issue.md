# Refine Issue Skill

Given a GitHub issue number (or the current issue being discussed), run a structured refinement conversation before any implementation begins.

## Usage

`/refine-issue <issue-number>`

If no issue number is given, use the issue currently being discussed in the conversation.

## Steps

Work through these phases in order. Do not move to the next phase until the current one is resolved.

### Phase 1: Fetch and read the issue

Use `gh issue view <number>` to get the full issue text. Read it carefully.

### Phase 2: Split check

Ask: can this issue be broken into two or more independent pieces that could ship separately?

Good signals that it should be split:
- It contains "and" connecting two distinct behaviours
- Part A must exist before Part B can be built (dependency order)
- Part A and Part B could be tested independently
- One part is pure data/storage and the other is behaviour on top of it

If it should be split: propose the split clearly, identify which part is the prerequisite, and ask the user whether to update the current issue and create a new one, or create two new ones. Do not proceed until this is resolved.

### Phase 3: Testability check

Ask: how would you test this? Can you write a unit or integration test that fails before the work and passes after?

If the answer is unclear or "no", surface that — untestable issues often signal fuzzy scope or missing design decisions. Do not block on this, but flag it.

### Phase 4: Value and alignment check

Ask:
- What does the learner actually gain from this?
- Does it align with the core goal (personalised learning that adapts to the learner over time)?
- Is there a simpler version that delivers most of the value?

Surface any concerns, but defer to the user's judgement.

### Phase 5: Design discussion

Only after phases 2-4 are resolved: discuss the implementation approach. Cover:
- Data model (if any new data is introduced)
- Where the logic lives (which module/layer)
- What changes at the boundary (CLI, API, or both)
- Any hard-to-reverse decisions that need to be made now vs. later

If any hard-to-reverse decisions are made (data store choice, storage format, module boundaries), propose capturing them as an ADR in `docs/decisions/`. Check the existing ADRs for the next number and format to follow.

Do not suggest editing any files during this phase unless the user explicitly asks.

### Phase 6: Commit breakdown

After the user confirms the design: propose a sequence of atomic, independently-testable commits that together implement the issue. Each commit should:
- Do one logical thing
- Leave the codebase in a working state
- Have a clear test that validates it

Present the breakdown as a numbered list. Ask the user to confirm or adjust before any implementation begins.

### Phase 7: Update the issue

After the user confirms the commit breakdown, append the agreed design and commit breakdown to the GitHub issue body.

1. Get the current body: `gh issue view <number> --json body -q .body`
2. Append two sections:

```
## Design
- Key decisions (data model, module location, notable tradeoffs)
- Dependencies on other issues (if any)

## Commits
1. ...
2. ...
```

3. Write back with `gh issue edit <number> --body "<updated body>"`

Confirm to the user once done.

### Phase 8: Move to Todo

After updating the issue, move it to "Todo" in the project board:

1. Get the item ID: `gh project item-list 6 --owner lmchoi --format json | python3 -c "import json,sys; items=json.load(sys.stdin)['items']; item=next((i for i in items if i.get('content',{}).get('number')==<number>),None); print(item['id'] if item else 'not found')"`
2. Set status to Todo: `gh project item-edit --project-id PVT_kwHOAHDUcM4BSQiR --id <item-id> --field-id PVTSSF_lAHOAHDUcM4BSQiRzg_2JWs --single-select-option-id 2488e2e8`

If the issue is not in the project yet, add it first: `gh project item-add 6 --owner lmchoi --url <issue-url>`

Confirm to the user once done.

## Notes

- This is a conversation, not a one-shot analysis. Pause and wait for user input at each phase.
- Keep proposals concrete — name the files, modules, and data models.
- Flag scope creep if the design discussion starts pulling in work that belongs in a different issue.

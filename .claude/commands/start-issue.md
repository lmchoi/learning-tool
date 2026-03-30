# Start Issue Skill

Given a refined GitHub issue number, create a worktree and branch, and move the issue to "In Progress" on the project board.

## Usage

`/start-issue <issue-number>`

The issue must already be refined (design and commit breakdown present in the issue body). If it hasn't been refined yet, run `/refine-issue` first.

## Steps

### Step 1: Fetch the issue

Run `gh issue view <number>` to get the full issue text. Read it carefully — you need the commit breakdown and any design notes.

If the issue body has no `## Commits` section, stop and tell the user to run `/refine-issue <number>` first.

### Step 2: Determine the branch name

Use the format `feat/<number>-<short-slug>` where the slug is a 2-4 word kebab-case summary of the issue title.

Examples:
- #144 "Capture-mode practice page" → `feat/144-capture-mode`
- #187 "Document database schemas" → `feat/187-schema-docs`

### Step 3: Create the worktree

```bash
git worktree add .claude/worktrees/<number>-<slug> -b feat/<number>-<slug>
```

If the branch already exists (worktree was previously created), just confirm it exists and proceed.

### Step 4: Move the issue to In Progress

1. Check if the issue is already in the project:
```bash
gh project item-list 6 --owner lmchoi --format json --limit 100 | python3 -c "
import json,sys
items=json.load(sys.stdin)['items']
item=next((i for i in items if i.get('content',{}).get('number')==<number>),None)
print(item['id'] if item else 'not found')
"
```

2. If not found, add it first:
```bash
gh project item-add 6 --owner lmchoi --url <issue-url>
```
Then re-run the lookup.

3. Set status to In Progress:
```bash
gh project item-edit --project-id PVT_kwHOAHDUcM4BSQiR --id <item-id> --field-id PVTSSF_lAHOAHDUcM4BSQiRzg_2JWs --single-select-option-id 194746c4
```

### Step 5: Confirm to the user

Tell the user:
- The branch name and worktree path
- That the issue has been moved to In Progress
- That they can now run `/implement-issue` in the worktree to start implementing

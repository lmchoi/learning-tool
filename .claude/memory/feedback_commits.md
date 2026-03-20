---
name: Small focused commits
description: Don't bundle unrelated changes into one big commit — each logical change should be its own commit
type: feedback
---

Don't commit everything in one go. Each logical change (each doc, each config change, each feature) gets its own commit with a focused message. This applies to docs, ADRs, conventions — each file or closely related set of files should be a separate commit.

If a fix is needed before a PR is raised, don't create a separate "fix" commit — use `git commit --fixup` and rebase to squash it into the original commit.

Run `git add` and `git commit` as separate tool calls — chaining them with `&&` breaks permission matching.

When addressing PR review feedback, split fixes into individual commits (one per logical change) rather than bundling them into a single "address PR review" commit. The user will then do `git rebase -i` themselves to squash each fix into its original commit. Do not attempt the rebase — hand the split commits to the user.

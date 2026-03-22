---
name: Use closing keywords in PRs
description: Always use GitHub closing keywords when a PR completes issues
type: feedback
---

When creating a PR that completes one or more issues, include `closes #<number>` lines in the PR body — not just `#<number>` references.

**Why:** GitHub only auto-closes issues on merge when closing keywords are present. Plain `#69` references are just links; they don't close anything. Four issues (#66, #69, #70, #87) were left open after PR #95 merged because the body used `**#69**` formatting instead of `closes #69`.

**How to apply:** In the PR body, add a "Closes" section with one `closes #<number>` per issue. Use `closes` (not `fixes` or `resolves`) for consistency with the PR template.

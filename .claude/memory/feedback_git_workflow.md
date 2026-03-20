---
name: Always branch and PR, never push to main
description: All work must be done on a branch with a PR — never push directly to main
type: feedback
---

Always create a branch first, do all commits there, then raise a PR. Never push directly to main. This applies even for setup/tooling commits.

Create the branch before writing any code — not after the commits are done.

Split `git add` and `git commit` into separate commands so the user can review what's being staged before approving the commit.

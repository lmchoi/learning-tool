---
name: Worktree setup steps
description: Steps to run when creating a new worktree or checkout of the learning-tool repo
type: project
---

After creating a new worktree or cloning into a new directory, symlink the shared contexts folder:

```bash
ln -s /home/bokchoi/Workspace/learning-tool/contexts contexts
```

This gives the app access to the ingested store at `contexts/store`, which is the default `STORE_DIR`.
The `contexts/` directory is gitignored so it is never committed — the symlink must be created manually each time.

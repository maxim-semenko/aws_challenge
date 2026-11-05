---
description: Implement one task from docs/tasks by delegating it to the agent named in its front matter
argument-hint: <task ID, e.g. T01-03>
---

Implement task `$ARGUMENTS`.

1. Find the file `docs/tasks/*/$ARGUMENTS-*.md` and read its front matter and body, its `design` and `spec` files.
2. Check the start gate (docs/PLAN.md "How the plan works"): `status` is not `Blocked`, every `depends_on` task is
   `Done`, the design doc status is `Accepted`. If any check fails, stop and report which one — do not implement.
3. Set the task to `In progress` in the task file and in the docs/PLAN.md index.
4. Delegate to the subagent named in `agent` with this prompt: the task file path, "read CLAUDE.md, the task, its
   design and spec; use skills <skills from front matter>; implement exactly the SCOPE".
5. When the agent returns: verify the Done invariants from CLAUDE.md §7 yourself (run build/tests that apply).
6. If the task's agent is `devops` or `backend`, delegate a review to the `architect` subagent.
7. Report to the owner in Russian: what changed (files), invariant results (or "not verified"), review findings,
   anything that needs the owner's go-ahead (deploy, commit). Set the task to `Review`. Never mark it `Done` and
   never commit or deploy without the owner's explicit approval.

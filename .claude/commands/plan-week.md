---
description: Turn a new curriculum week into requirements, design docs, specs and tasks
argument-hint: <week number>
---

Plan curriculum week $ARGUMENTS. The owner provides the assignment text or screenshot in the conversation.

1. Export the assignment as given (translated to English) to `docs/requirements/week-NN-<name>.md`, with a
   traceability table requirement → spec at the end.
2. Delegate to the `architect` subagent: compare the requirements with docs/ARCHITECTURE.md and the existing
   design docs; list conflicts; add each unresolved conflict as a `Q-xx` in docs/RISKS.md with options and a
   recommendation.
3. Architect drafts or updates `docs/design/<feature>.md` per major feature (seven sections), status `Draft`.
4. Architect writes `docs/specs/NN-<name>.md` (six sections, numbered ACs). Every endpoint that creates or updates
   data lists every field the frontend sends.
5. Architect writes tasks in a new phase folder `docs/tasks/P<n>-<phase>/T<nn>-<mm>-<name>.md` with front matter
   (agent, skills, depends_on, blocked_by, design, spec, acceptance) and the three layers; one tester acceptance task
   per week.
6. Update the docs/PLAN.md phases table, graph and index; run `/check-docs`.
7. Report to the owner in Russian: new files, the open questions to answer, which tasks can start now. Nothing is
   implemented until the design docs are `Accepted`.

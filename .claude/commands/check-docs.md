---
description: Check the documentation for consistency and duplication against the rules in CLAUDE.md §7
---

Run the consistency checks from CLAUDE.md §7 "Consistency rules" over `CLAUDE.md`, `docs/` and `.claude/` and
report findings. Do not fix anything unless the owner asks.

Check:
1. Every task file under `docs/tasks/` has the required front matter fields and the three layers
   `// BUSINESS CONTEXT`, `// TECHNICAL CONSTRAINTS`, `// SCOPE`.
2. Task front matter and the docs/PLAN.md index agree on status, depends_on, blocked_by, agent, skills.
3. Every `blocked_by` item is an Open `Q-xx` in docs/RISKS.md; every Open `Q-xx` lists the tasks it blocks and they
   match; a task with an open blocker has status `Blocked`.
4. Every task links an existing design doc (or `null` with a reason) and spec; every AC id it lists exists in the spec.
5. Every design doc has the seven sections; every spec has the six sections.
6. Duplication: a fact (stack, conventions, design tokens, decisions) stated in more than one place; any colour/font
   literal outside CLAUDE.md §5; any relative link that points to a missing file.
7. Every task whose SCOPE adds an AWS service, library, tool, internal interface or schema lists a skill file in
   SCOPE and DoD (skills ownership rule).
8. Every skill named in a task or agent exists in `.claude/skills/`; every file in `.claude/` has the YAML front
   matter required by CLAUDE.md §8 "Skill file format".

Output a table: check → result → file:line → suggested fix (pointer to the single home).

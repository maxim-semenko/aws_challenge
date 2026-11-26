---
id: T05-05
title: "Week 5 acceptance check"
phase: P5-semantic-search
status: Todo
agent: tester
skills: [test-master]
depends_on: [T05-01, T05-02, T05-03, T05-04]
blocked_by: []
design: null  # acceptance task, verifies specs 12-13 and the regressions of specs 04, 08, 09, 10, 11
spec: [../../specs/12-chat-api.md, ../../specs/13-chat-page.md]
acceptance: [AC-12.1, AC-12.2, AC-12.3, AC-12.4, AC-12.5, AC-12.6, AC-12.7, AC-12.8, AC-12.9, AC-12.10, AC-12.11, AC-12.12, AC-13.1, AC-13.2, AC-13.3, AC-13.4, AC-13.5, AC-08.1, AC-08.6, AC-08.9, AC-09.1, AC-10.2, AC-11.1, AC-04.10]
---
# T05-05 — Week 5 acceptance check

## // BUSINESS CONTEXT

Week 5 ("Semantic search form") is done when W5-G1, W5-G2, S1 … S4 and the project's statistics example are proven
on `dev` by someone other than the implementer. The report states the deviations honestly: direct Bedrock call
instead of a Bedrock Agent (Q-21 A, ADR-021), Nova Micro instead of Claude 3 Sonnet (ADR-022), < 1 s only for the vector path, the `sql` keyword rule.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). Local ACs (pytest of all functions, zip builds and hashes,
  `npm run build` / `npm test`, code review items, `git grep` for secrets) run by the tester; AWS-side ACs from owner
  evidence in T05-01 / T05-03 Notes (by pointer), only missing evidence requested.
- Each AC: pass / fail / not verifiable + source + trimmed output; account ids masked; no personal data.
- Regressions: the moved shared modules (AC-08.1, AC-10.2, AC-11.1 by pytest; AC-08.6, AC-08.9 after the admin
  re-upload), SPA (AC-09.1, AC-04.10).

## // SCOPE

**Implement**
- Owner checklist for missing evidence; report table AC → result → evidence in Notes; requirement coverage W5-G1,
  W5-G2, S1 … S4, project requirement

**Exclude**
- Fixing defects (reported to the owning task); E2E suite

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All listed ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-25: created by Week 5 planning; `Todo` (no open blocker of its own; waits for T05-01 … T05-04 `Done`).

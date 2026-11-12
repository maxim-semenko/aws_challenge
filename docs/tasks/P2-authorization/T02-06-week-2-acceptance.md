---
id: T02-06
title: "Week 2 acceptance check"
phase: P2-authorization
status: Todo
agent: tester
skills: [test-master]
depends_on: [T02-03, T02-05]
blocked_by: []
design: null  # acceptance task, verifies specs 04 and 05
spec: [../../specs/04-user-registration-and-sign-in.md, ../../specs/05-protected-api.md]
acceptance: [AC-04.*, AC-05.*]
---
# T02-06 — Week 2 acceptance check

## // BUSINESS CONTEXT

Week 2 is done only when registration, sign-in, the personal page and the protected API are proven on `dev` by
someone other than the implementer. The report is what the owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). AWS-side ACs are verified from evidence the owner provides
  (console screenshots, outputs of the `curl` and log searches the owner runs from the tester's checklist); local ACs
  (AC-04.4, AC-04.10, AC-04.11, AC-05.12: SPA build/tests, pytest, `package.json`) are run by the tester itself.
  Test users are signed up by the owner through the SPA (the feature under test).
- Each criterion gets pass/fail plus evidence (source, command or screenshot reference, trimmed output); account ids
  masked; no tokens, passwords or test-user personal data beyond the test e-mail's domain in the report.
- A failed criterion is reported back to the owning task, not fixed here.

## // SCOPE

**Implement**
- Checklist for the owner (what to show per AWS-side AC); verify every AC of specs 04 and 05 with two fresh test
  users (one is added to `admin` by the owner); write the report in Notes (table: AC → result → evidence)
- Regression: the `admin` probe (AC-05.10) and the spec 01 home page with the new build

**Exclude**
- Fixing defects, automated E2E suite (later phase)

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

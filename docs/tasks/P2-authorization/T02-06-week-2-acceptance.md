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

- Read-only against AWS: `describe`/`get`/`list`, `lambda invoke` of the `admin` probe with `{}`, `curl`, log
  queries. Signing up test users through the SPA is allowed (it is the feature under test); no other changes.
- Each criterion gets pass/fail plus evidence (command and trimmed output); account ids masked; no tokens, passwords
  or test-user personal data beyond the test e-mail's domain in the report.
- A failed criterion is reported back to the owning task, not fixed here.

## // SCOPE

**Implement**
- Run every AC of specs 04 and 05 on dev with two fresh test users (one is added to `admin` by the owner);
  write the report in Notes (table: AC → result → evidence)
- Regression: the `admin` probe (AC-05.10) and the spec 01 home page with the new build

**Exclude**
- Fixing defects, automated E2E suite (later phase)

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

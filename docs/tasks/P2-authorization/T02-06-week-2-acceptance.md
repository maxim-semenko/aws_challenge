---
id: T02-06
title: "Week 2 acceptance check"
phase: P2-authorization
status: Todo
agent: tester
skills: [test-master]
depends_on: [T02-01, T02-03, T02-04, T02-05]
blocked_by: []
design: null  # acceptance task, verifies specs 04 and 05
spec: [../../specs/04-user-registration-and-sign-in.md, ../../specs/05-protected-api.md]
acceptance: [AC-04.1, AC-04.2, AC-04.4, AC-04.5, AC-04.6, AC-04.8, AC-04.9, AC-04.10, AC-04.11, AC-05.1, AC-05.2, AC-05.3, AC-05.4, AC-05.5, AC-05.6]
---
# T02-06 — Week 2 acceptance check

## // BUSINESS CONTEXT

Week 2 (owner decision 2026-11-13: the curriculum topic only — Cognito User Pool with Amplify Auth, HTTP API with a
JWT authorizer) is done only when registration, sign-in, the personal page and the authorizer are proven on `dev` by
someone other than the implementer. The report is what the owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). AWS-side ACs are verified from evidence the owner provides (console
  screenshots, the browser-console status codes from the T02-03 evidence checklist); local ACs (AC-04.4, AC-04.10,
  AC-04.11: SPA build/tests, `package.json`) are run by the tester itself. Test users are signed up by the owner
  through the deployed SPA (the feature under test).
- Evidence already recorded in T02-01, T02-03, T02-04 and T02-05 Notes is reused (pointer, not a copy); only what is
  missing is requested from the owner.
- Each criterion gets pass/fail plus evidence (source, command or screenshot reference, trimmed output); account ids
  masked; no tokens, passwords or test-user personal data beyond the test e-mail's domain in the report.
- A failed criterion is reported back to the owning task, not fixed here.

## // SCOPE

**Implement**
- Checklist for the owner: only the evidence still missing (see the owning tasks' Notes)
- Verify every AC listed in the front matter (spec 04 without the withdrawn AC-04.3/AC-04.7; spec 05 as reduced
  2026-11-13); write the report in Notes (table: AC → result → evidence)
- Regression: the spec 01 home page with the current build

**Exclude**
- Week 3 items (group `admin`, `/api/...` endpoints, role line, Lambda code, logs), fixing defects, automated E2E
  suite (later phase)

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All listed ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

---
id: T01-06
title: "Week 1 acceptance check"
phase: P1-environment
status: Todo
agent: tester
skills: [test-master]
depends_on: [T00-01, T01-04, T01-05]
blocked_by: []
design: null  # acceptance task, verifies specs 01–03
spec: [../../specs/01-spa-delivery.md, ../../specs/02-database-connectivity.md, ../../specs/03-local-aws-access.md]
acceptance: [AC-01.*, AC-02.*, AC-03.*]
---
# T01-06 — Week 1 acceptance check

## // BUSINESS CONTEXT

Week 1 is done only when every acceptance criterion is proven on the deployed `dev` environment by someone other than
the implementer. The report is what the owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- Read-only against AWS: only `describe`/`get`/`invoke`/`curl` commands, no changes to resources.
- Each criterion gets pass/fail plus evidence (command and trimmed output); account ids masked; no secrets.
- A failed criterion is reported back to the owning task, not fixed here.

## // SCOPE

**Implement**
- Run every AC of specs 01, 02, 03; write the report in Notes (table: AC → result → evidence)
- Check the cost guard: budget alert exists; note how to destroy the stacks

**Exclude**
- Fixing defects, automated E2E suite (later phase)

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

---
id: T01-06
title: "Week 1 acceptance check and record of the manual build"
phase: P1-environment
status: Todo
agent: tester
skills: [test-master]
depends_on: []  # verifies the manually built environment; the Week 1 build tasks are in Review until this report exists (Q-12)
blocked_by: []
design: null  # acceptance task, verifies specs 01–03
spec: [../../specs/01-spa-delivery.md, ../../specs/02-database-connectivity.md, ../../specs/03-local-aws-access.md]
acceptance: [AC-01.*, AC-02.*, AC-03.*]
---
# T01-06 — Week 1 acceptance check and record of the manual build

## // BUSINESS CONTEXT

Week 1 was built manually by the owner in the AWS console (Q-12, option C). It is done only when every acceptance
criterion is proven on the deployed environment by someone other than the implementer, and the actual values of the
build are written down — several closed decisions (Q-01, Q-03, Q-04, Q-07, Q-08, Q-09, Q-10, Q-11) say "value to be
recorded by T01-06", and Week 2 tasks need region, names and ARNs. The report is what the owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- Read-only against AWS: only `describe`/`get`/`list`/`invoke` (probe functions with `{}`)/`curl`, no changes to
  resources.
- Each criterion gets pass/fail plus evidence (command and trimmed output); account ids masked; no secrets.
- AC-01.4 and AC-02.9 (IaC) are recorded as *deferred to T00-03* (Q-12 C), not as failures.
- A failed criterion is reported back to the owning task, not fixed here.

## // SCOPE

**Implement**
- Run every AC of specs 01, 02, 03; write the report in Notes (table: AC → result → evidence)
- Record the facts of the build in Notes: region; Git hosting and repository URL; Amplify app id and domain;
  environment(s) and resource names; VPC CIDR, subnets, NAT, route tables, security groups; PostgreSQL version and
  instance class; RDS Proxy settings; per function: name, runtime, architecture, memory, timeout, handler, VPC
  config, role and policies, env var names (no values of secrets), log group retention, the probe's database driver;
  which SDK(s) are configured locally (AC-03.2)
- List the scope items of T00-01, T00-02, T01-01, T01-02, T01-04, T01-05 the manual build did not produce (e.g.
  skill files, README section)
- Check the cost guard: budget alert exists; note what runs 24/7 and how to stop it

**Exclude**
- Fixing defects, automated E2E suite (later phase), updating RISKS.md (the architect copies the recorded values)

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All ACs pass, are deferred per Q-12, or failures are recorded against their tasks and the owner decides
- [ ] Facts of the build recorded
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

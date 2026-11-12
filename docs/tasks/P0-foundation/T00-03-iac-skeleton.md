---
id: T00-03
title: "Codify the manually built resources in IaC"
phase: P0-foundation
status: Blocked
agent: devops
skills: [cloud-architect, devops-engineer]
depends_on: [T01-06]
blocked_by: [Q-02]
design: ../../design/backend-foundation.md
spec: [../../specs/01-spa-delivery.md, ../../specs/02-database-connectivity.md]
acceptance: [AC-01.4, AC-02.9]
---
# T00-03 — Codify the manually built resources in IaC

> **BLOCKED** by [Q-02](../../RISKS.md#q-02). Re-scoped 2026-11-12 by Q-12 (option C): Week 1 was built manually
> and Week 2 is built with recorded AWS CLI runbooks; this is the later dedicated IaC task. The scope below is
> refined (and Week 2 resources added) when Q-02 is answered and the task is planned.

## // BUSINESS CONTEXT

The environment must be reproducible from code, so it can be removed when idle to save money and recreated in
minutes (R-06), and so that console edits stop drifting from what the repository says (R-15).

## // TECHNICAL CONSTRAINTS

- Tool per Q-02 (recommended: AWS CDK in Python, same language as the Lambdas).
- **Import** existing resources, do not recreate them: the Cognito User Pool cannot be recreated without losing its
  users, and recreating RDS/Proxy changes endpoints. Input: the facts recorded by T01-06 and the runbooks in the
  Week 2 devops task Notes.
- Account, region and environment come from configuration, never from code. Naming and tags per CLAUDE.md §7,
  applied in one place.
- Policy checks (e.g. cdk-nag) on `synth`; suppressions need a written reason. No secrets in context files.
- Show every plan/diff to the owner and wait for the go-ahead before any deploy (CLAUDE.md §3.8).

## // SCOPE

**Implement**
- IaC project, environment configuration, naming and tags
- Network, Data, Compute and Hosting resources of Week 1 imported with no change to the running resources
- Skill file for the IaC tool (skills ownership rule)

**Exclude**
- New resources or behaviour changes; Week 2 resources until the task is refined

**Interfaces that must match**
- Resource names and settings exactly as recorded by T01-06.

## Definition of Done

- [ ] AC-01.4 and AC-02.9 hold; a diff after import shows no change to the running resources
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

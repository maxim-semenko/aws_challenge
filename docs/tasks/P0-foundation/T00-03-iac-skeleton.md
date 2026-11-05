---
id: T00-03
title: "IaC skeleton with environment configuration"
phase: P0-foundation
status: Blocked
agent: devops
skills: [cloud-architect, devops-engineer]
depends_on: [T00-01]
blocked_by: [Q-02, Q-03, Q-07]
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.9]
---
# T00-03 — IaC skeleton with environment configuration

> **BLOCKED** by [Q-02](../../RISKS.md#q-02), [Q-03](../../RISKS.md#q-03), [Q-07](../../RISKS.md#q-07).

## // BUSINESS CONTEXT

All Week 1 infrastructure must be reproducible from code (no console clicking), so it can be destroyed when idle to
save money and recreated in minutes. This task gives every infrastructure task the same base.

## // TECHNICAL CONSTRAINTS

- Tool per Q-02 (recommended: AWS CDK v2 in Java 21, Gradle subproject `infra` in the existing multi-project build).
- Account, region and environment come from configuration (CDK context), never from code.
- Naming and tags per CLAUDE.md §7, applied in one place.
- cdk-nag (AwsSolutions) runs on `synth`; suppressions need a written reason.
- No secrets in context files.

## // SCOPE

**Implement**
- `infra` module, app entry point, empty stacks Network, Data, Compute, Hosting
- Environment config, naming helper, tags
- `cdk bootstrap` of the dev account/region; deploy of the empty stacks
- Skill file for the IaC tool (skills ownership rule, CLAUDE.md)

**Exclude**
- Any real resource (T01-01 … T01-05)

**Interfaces that must match**
- Stack names and the cross-stack reference pattern used by T01-01 … T01-05.

## Definition of Done

- [ ] AC-02.9 holds for the empty stacks; empty stacks deployed to dev
- [ ] Skill file added
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

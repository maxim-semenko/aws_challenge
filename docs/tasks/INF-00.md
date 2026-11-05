# INF-00 — CDK application skeleton (`infra` module)

> **BLOCKED** by [Q-02](../RISKS.md#q-02). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | INF — infrastructure as code |
| Milestone | M0 |
| Role | OPS + ARCH |
| Size | M |
| Depends on | [ARCH-01](ARCH-01.md) |
| Blocked by | [Q-02](../RISKS.md#q-02) |
| Unblocks | [OPS-02](OPS-02.md), [INF-01](INF-01.md) |
| Risks watched | — |
| Goals | — |
| References | ADR-001 |

## Goal

An empty but deployable IaC project that all infrastructure tasks build on.

## Scope

**In scope**

- Gradle subproject `infra` (CDK v2, Java 21)
- Stacks: Network, Data, Auth, Compute, Api, Hosting (empty)
- `cdk.json`, cdk-nag (AwsSolutions) wired in
- `cdk bootstrap` of the dev account/region

**Out of scope**

- Actual resources (INF-01 … INF-08)

## Plan

- [ ] Create the module and app entry point
- [ ] Add stack classes and cross-stack wiring pattern
- [ ] Bootstrap and deploy empty stacks

## Definition of Done

- [ ] `cdk synth` passes with cdk-nag
- [ ] Empty stacks deploy to dev
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

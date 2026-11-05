# OPS-03 — Continuous delivery of the backend

> **BLOCKED** by [Q-07](../RISKS.md#q-07). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | OPS — repository, CI/CD, cost |
| Milestone | M3 |
| Role | OPS |
| Size | M |
| Depends on | [OPS-02](OPS-02.md), [INF-05](INF-05.md), [BE-05](BE-05.md) |
| Blocked by | [Q-07](../RISKS.md#q-07) |
| Unblocks | — |
| Risks watched | [R-02](../RISKS.md#2-risk-register) |
| Goals | G4, G5 |
| References | ADR-008 |

## Goal

A merge to `main` deploys the backend and infrastructure without manual steps and can be rolled back.

## Scope

**In scope**

- Build `backend-lambda.zip`
- `cdk deploy` with an OIDC-assumed role (no long-lived keys)
- Invoke the `migrate` function before switching traffic
- Publish versions and move the `live` alias (SnapStart)
- Rollback procedure (previous alias version)

**Out of scope**

- Frontend delivery (Amplify builds itself, FE-06)

## Plan

- [ ] Create the deploy role with OIDC trust
- [ ] Add the deploy job after CI
- [ ] Document rollback in README

## Definition of Done

- [ ] Merge to `main` updates dev
- [ ] Failed migration stops the rollout
- [ ] Rollback tested once
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

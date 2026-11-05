# INF-05 — ComputeStack: Lambda functions

> **BLOCKED** by [Q-08](../RISKS.md#q-08), [Q-10](../RISKS.md#q-10). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | INF — infrastructure as code |
| Milestone | M1 |
| Role | OPS + BE |
| Size | M |
| Depends on | [INF-02](INF-02.md), [BE-00](BE-00.md) |
| Blocked by | [Q-08](../RISKS.md#q-08), [Q-10](../RISKS.md#q-10) |
| Unblocks | [OPS-03](OPS-03.md), [INF-06](INF-06.md), [INF-07](INF-07.md), [BE-12](BE-12.md), [OBS-01](OBS-01.md), [BE-13](BE-13.md) |
| Risks watched | [R-01](../RISKS.md#2-risk-register), [R-02](../RISKS.md#2-risk-register), [R-08](../RISKS.md#2-risk-register) |
| Goals | G4 |
| References | ARCHITECTURE.md §3.2, ADR-002, [Week 1 spec](../specs/week-01-environment.md) S5, S7, AC-5, AC-7 |

## Goal

The four functions from one artifact run inside the isolated subnets with least-privilege roles.

## Scope

**In scope**

- Functions `chatbot`, `admin`, `sync`, `migrate` from `backend-lambda.zip`
- Java 21, arm64, memory/timeouts per ARCHITECTURE.md §10
- VPC app subnets + `sg-lambda`
- One IAM role per function
- SnapStart, published versions, alias `live`
- Log groups with 14-day retention created by IaC
- Environment variables (no secrets)

**Out of scope**

- Bedrock permissions (INF-07)
- API routes (INF-06)

## Plan

- [ ] Implement the stack
- [ ] Invoke each function once
- [ ] Record cold/warm durations

## Definition of Done

- [ ] All functions run in isolated subnets
- [ ] Each has its own role
- [ ] Log groups exist with retention set
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

- 2026-11-05: Week 1 needs only `admin`, `chatbot`, `sync` with the handlers from BE-13; `migrate`, SnapStart and
  the Spring artifact can follow later. The exact Week 1 subset is fixed when Q-10 is answered.

# INF-07 — Bedrock access from the VPC

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | INF — infrastructure as code |
| Milestone | M4 |
| Role | OPS |
| Size | S |
| Depends on | [INF-02](INF-02.md), [INF-05](INF-05.md), [ARCH-02](ARCH-02.md) |
| Blocked by | — |
| Unblocks | [OPS-04](OPS-04.md), [BE-07](BE-07.md) |
| Risks watched | [R-05](../RISKS.md#2-risk-register), [R-09](../RISKS.md#2-risk-register) |
| Goals | G7 |
| References | ARCHITECTURE.md §3.6 |

## Goal

`chatbot` can call Titan v2 privately and nothing else in Bedrock.

## Scope

**In scope**

- IAM `bedrock:InvokeModel` on the Titan v2 model ARN for `chatbot` only
- Endpoint policy limiting the endpoint to that model
- Verification invoke from the function

**Out of scope**

- Other models (BE-11)

## Plan

- [ ] Add policies
- [ ] Invoke a test embedding from the function

## Definition of Done

- [ ] Embedding call succeeds from inside the VPC
- [ ] Other functions get AccessDenied
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

# OPS-04 — Cost control: estimate, stop and start the stack

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | OPS — repository, CI/CD, cost |
| Milestone | M5 |
| Role | OPS |
| Size | S |
| Depends on | [INF-03](INF-03.md), [INF-07](INF-07.md) |
| Blocked by | — |
| Unblocks | — |
| Risks watched | [R-06](../RISKS.md#2-risk-register) |
| Goals | — |
| References | ARCHITECTURE.md §10 |

## Goal

Keep the learning environment cheap when nobody uses it.

## Scope

**In scope**

- Monthly cost estimate per component (RDS, RDS Proxy, interface endpoints, Lambda, API GW, Amplify)
- Scripts: stop/start RDS; destroy/re-create Proxy and endpoint stacks
- README section

**Out of scope**

- Production cost optimisation

## Plan

- [ ] Estimate with AWS Pricing Calculator
- [ ] Write scripts
- [ ] Test stop → start → smoke

## Definition of Done

- [ ] Estimate recorded in ARCHITECTURE.md §10
- [ ] Scripts work end-to-end
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

# INF-02 — NetworkStack: isolated VPC, security groups, VPC endpoints

> **BLOCKED** by [Q-08](../RISKS.md#q-08). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | INF — infrastructure as code |
| Milestone | M1 |
| Role | OPS |
| Size | M |
| Depends on | [INF-01](INF-01.md) |
| Blocked by | [Q-08](../RISKS.md#q-08) |
| Unblocks | [INF-03](INF-03.md), [INF-05](INF-05.md), [INF-07](INF-07.md) |
| Risks watched | [R-09](../RISKS.md#2-risk-register) |
| Goals | G2, G4 |
| References | ARCHITECTURE.md §4, ADR-005, [Week 1 spec](../specs/week-01-environment.md) S3 |

## Goal

A VPC with no route to the internet, where Lambda, RDS Proxy and RDS live.

## Scope

**In scope**

- VPC `10.0.0.0/16`, 2 AZs, `PRIVATE_ISOLATED` subnets for app and data tiers
- No IGW, no NAT
- Security groups `sg-lambda`, `sg-proxy`, `sg-db`, `sg-endpoints` per the matrix
- Interface endpoints `bedrock-runtime`, `secretsmanager` with private DNS

**Out of scope**

- Bastion host (only if needed later)

## Plan

- [ ] Implement the stack
- [ ] Export subnet and SG references
- [ ] cdk-nag review

## Definition of Done

- [ ] Synthesised template contains no IGW/NAT
- [ ] SG rules exactly match ARCHITECTURE.md §4
- [ ] Endpoints resolve privately from inside the VPC
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

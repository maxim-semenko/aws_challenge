---
id: T01-01
title: "Network stack: VPC, subnets, NAT, security groups"
phase: P1-environment
status: Blocked
agent: devops
skills: [cloud-architect]
depends_on: [T00-03]
blocked_by: [Q-08]
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.1, AC-02.2]
---
# T01-01 — Network stack: VPC, subnets, NAT, security groups

> **BLOCKED** by [Q-08](../../RISKS.md#q-08).

## // BUSINESS CONTEXT

Lambda, RDS Proxy and RDS must not be reachable from the internet (G2, S3). A wrong route table or an open security
group exposes the database; a missing outbound path makes Secrets Manager calls time out and the probe fail.

## // TECHNICAL CONSTRAINTS

- Layout exactly as the accepted Q-08 option in [backend-foundation](../../design/backend-foundation.md) (proposed:
  1 public subnet with one NAT, 2 private-with-egress subnets, 2 AZs, `10.0.0.0/16`).
- Security groups exactly per the design matrix; no `0.0.0.0/0` inbound anywhere.
- No public IP auto-assignment in private subnets. cdk-nag findings fixed or suppressed with a reason.

## // SCOPE

**Implement**
- VPC, subnets, IGW, NAT, route tables; `sg-lambda`, `sg-proxy`, `sg-db`
- Exports: VPC, private subnet ids, the three security groups
- Skill file `vpc-network` (layout, SG matrix, how to add a new path; skills ownership rule)

**Exclude**
- VPC endpoints, bastion, flow logs

**Interfaces that must match**
- Exported references consumed by T01-02 (Data) and T01-04 (Compute).

## Definition of Done

- [ ] AC-02.1, AC-02.2 (SG part) verified on the deployed stack, evidence in Notes
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

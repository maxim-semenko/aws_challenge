---
id: T01-04
title: "Compute: three functions, roles, log groups"
phase: P1-environment
status: Done
agent: devops
skills: [cloud-architect]
depends_on: [T01-02]
blocked_by: []
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.4, AC-02.5, AC-02.6, AC-02.7]
---
# T01-04 — Compute: three functions, roles, log groups

> **2026-11-12 — built manually by the owner** in the AWS console ([Q-12](../../RISKS.md#q-12), option C), with the
> function code written in Python in the console (Q-10 closed, ADR-015; the Java handler task T01-03 was deleted as
> obsolete). T01-06 records the facts of the build and verifies the ACs; the owner sets `Done` from that evidence.
> Scope items the manual build did not produce (e.g. the skill file) appear as open items in T01-06; the owner waives
> them or asks devops to deliver them.

## // BUSINESS CONTEXT

The functions `admin`, `chatbot`, `sync` are the backbone the later weeks build on (S5). Their roles and network
placement decide whether the backend is private and least-privileged; their log groups are where every incident is
investigated (S7).

## // TECHNICAL CONSTRAINTS

- Python runtime (version, architecture, memory and timeout as built (ARCHITECTURE §4); target Python 3.13 per
  ADR-015), private subnets + `sg-lambda`.
- One IAM role per function: `AWSLambdaVPCAccessExecutionRole` + `secretsmanager:GetSecretValue` on the DB secret ARN
  only. No wildcard resources.
- Log groups `/aws/lambda/<name>`, retention ≥ 7 days (S7; 14 days proposed).
- Env vars `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_SECRET_ARN` (spec 02); no secret values.

## // SCOPE

**Implement**
- Functions, roles, log groups; `admin` runs the `SELECT 1` probe, `chatbot` and `sync` log and return
- Invoke each function once; invoke `admin` and record response, log line and proxy `ClientConnections`
- Skill file `lambda-functions` (runtime, roles, log groups, how to add a function; skills ownership rule)

**Exclude**
- API Gateway, `migrate` function, bringing the code into Git (`admin`: Week 3)

**Interfaces that must match**
- Function names per ARCHITECTURE §4 (`aws-challenge-<function>`).

## Definition of Done

- [ ] AC-02.4 … AC-02.7 verified, evidence in Notes
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-12: `Done` — accepted by the owner (evidence: owner's statement + VPC console screenshot; facts in [ARCHITECTURE §4](../../ARCHITECTURE.md#4-network)); built manually; agents have no AWS access.

---
id: T01-04
title: "Compute stack: three functions, roles, log groups"
phase: P1-environment
status: Todo
agent: devops
skills: [cloud-architect]
depends_on: [T01-02, T01-03]
blocked_by: []
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.4, AC-02.5, AC-02.6, AC-02.7]
---
# T01-04 — Compute stack: three functions, roles, log groups

## // BUSINESS CONTEXT

The functions `admin`, `chatbot`, `sync` are the backbone the later weeks build on (S5). Their roles and network
placement decide whether the backend is private and least-privileged; their log groups are where every incident is
investigated (S7).

## // TECHNICAL CONSTRAINTS

- Runtime `java21`, arm64, 512 MB, timeout 15 s, private subnets + `sg-lambda`.
- One IAM role per function: `AWSLambdaVPCAccessExecutionRole` + `secretsmanager:GetSecretValue` on the DB secret ARN
  only. No wildcard resources.
- Log groups `/aws/lambda/<name>` created by IaC **before** the functions, retention 14 days.
- Env vars `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_SECRET_ARN` from T01-02 outputs; no secret values.

## // SCOPE

**Implement**
- Functions, roles, log groups from the T01-03 zip
- Deploy and invoke each function once; invoke `admin` and record response, log line and proxy `ClientConnections`
- Skill file `lambda-functions` (runtime, roles, log groups, how to add a function; skills ownership rule)

**Exclude**
- API Gateway, SnapStart/aliases, `migrate` function, Spring artifact

**Interfaces that must match**
- Function names `awsch-dev-admin`, `awsch-dev-chatbot`, `awsch-dev-sync`.

## Definition of Done

- [ ] AC-02.4 … AC-02.7 verified, evidence in Notes
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

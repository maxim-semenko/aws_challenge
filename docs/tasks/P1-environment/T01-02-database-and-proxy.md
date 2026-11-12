---
id: T01-02
title: "Data stack: RDS PostgreSQL, secret, RDS Proxy"
phase: P1-environment
status: Review
agent: devops
skills: [cloud-architect, postgres-pro]
depends_on: [T01-01]
blocked_by: []
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.2, AC-02.3]
---
# T01-02 — Data stack: RDS PostgreSQL, secret, RDS Proxy

> **2026-11-12 — built manually by the owner** in the AWS console ([Q-12](../../RISKS.md#q-12), option C).
> T01-06 records the facts of the build and verifies the ACs; the owner sets `Done` from that evidence.
> Constraints and ACs that assume IaC (stacks, outputs) are deferred to T00-03. Scope items the manual build did not
> produce (e.g. the skill file) appear as open items in T01-06; the owner waives them or asks devops to deliver them.

## // BUSINESS CONTEXT

The application database must be reachable only through RDS Proxy (G5, S4), which pools connections for Lambda. RDS
and the proxy are the biggest Week 1 cost (~$40/month), so the stack must be cheap and easy to destroy.

## // TECHNICAL CONSTRAINTS

- Engine major per Q-09 (closed: PostgreSQL 14; support deadline in R-14); `db.t4g.micro`, single-AZ, 20 GB gp3, encrypted, 7-day backups, `PubliclyAccessible=false`,
  deletion protection off in `dev` (the stack must be destroyable).
- Master credentials generated into Secrets Manager; never output or logged.
- RDS Proxy: secret auth, `RequireTLS=true`, idle client timeout 30 min, target = the instance, in the private
  subnets with `sg-proxy`.
- Local `docker-compose.yml` runs PostgreSQL 17; its alignment with the RDS major is tracked in R-14, not here.

## // SCOPE

**Implement**
- DB subnet group, instance, secret, proxy, target group
- Outputs: proxy endpoint, secret ARN, database name
- Skill file `rds-proxy` (instance, secret, proxy settings, how to connect for maintenance; skills ownership rule)

**Exclude**
- pgvector, schema, IAM database authentication, Multi-AZ

**Interfaces that must match**
- Outputs consumed by T01-04 as `DB_PROXY_ENDPOINT`, `DB_SECRET_ARN`, `DB_NAME`.

## Definition of Done

- [ ] AC-02.2 (RDS part), AC-02.3 verified, evidence in Notes
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

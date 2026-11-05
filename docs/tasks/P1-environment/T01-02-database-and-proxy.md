---
id: T01-02
title: "Data stack: RDS PostgreSQL, secret, RDS Proxy"
phase: P1-environment
status: Blocked
agent: devops
skills: [cloud-architect, postgres-pro]
depends_on: [T01-01]
blocked_by: [Q-09]
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.2, AC-02.3]
---
# T01-02 — Data stack: RDS PostgreSQL, secret, RDS Proxy

> **BLOCKED** by [Q-09](../../RISKS.md#q-09).

## // BUSINESS CONTEXT

The application database must be reachable only through RDS Proxy (G5, S4), which pools connections for Lambda. RDS
and the proxy are the biggest Week 1 cost (~$40/month), so the stack must be cheap and easy to destroy.

## // TECHNICAL CONSTRAINTS

- Engine major per Q-09; `db.t4g.micro`, single-AZ, 20 GB gp3, encrypted, 7-day backups, `PubliclyAccessible=false`,
  deletion protection off in `dev` (the stack must be destroyable).
- Master credentials generated into Secrets Manager; never output or logged.
- RDS Proxy: secret auth, `RequireTLS=true`, idle client timeout 30 min, target = the instance, in the private
  subnets with `sg-proxy`.
- Local `docker-compose.yml` and Testcontainers must use the same PostgreSQL major (change them if Q-09 ≠ 17).

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

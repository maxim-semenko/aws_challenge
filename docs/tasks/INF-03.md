# INF-03 — DataStack: RDS PostgreSQL, secret, RDS Proxy

> **BLOCKED** by [Q-08](../RISKS.md#q-08), [Q-09](../RISKS.md#q-09). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | INF — infrastructure as code |
| Milestone | M1 (pulled forward from M3 for Week 1, 2026-11-05) |
| Role | OPS |
| Size | M |
| Depends on | [INF-02](INF-02.md) |
| Blocked by | [Q-08](../RISKS.md#q-08), [Q-09](../RISKS.md#q-09) |
| Unblocks | [OPS-04](OPS-04.md), [INF-09](INF-09.md), [DB-02](DB-02.md), [BE-03](BE-03.md), [BE-13](BE-13.md) |
| Risks watched | [R-06](../RISKS.md#2-risk-register), [R-07](../RISKS.md#2-risk-register) |
| Goals | G5, G6 |
| References | ARCHITECTURE.md §3.5, ADR-006, [Week 1 spec](../specs/week-01-environment.md) S4, AC-4 |

## Goal

A private PostgreSQL with pgvector reachable only through RDS Proxy over TLS.

## Scope

**In scope**

- RDS PostgreSQL (major version per Q-09; must be supported by RDS Proxy, see R-07), `db.t4g.micro`, encrypted, 7-day backups
- Generated master secret in Secrets Manager
- RDS Proxy: TLS required, secret auth, idle timeout 30 min
- Outputs: proxy endpoint, secret ARN

**Out of scope**

- IAM authentication to the proxy (INF-09)
- Multi-AZ

## Plan

- [ ] Verify Proxy engine-version support
- [ ] Implement the stack
- [ ] Smoke-test `CREATE EXTENSION vector` via the proxy

## Definition of Done

- [ ] Proxy reachable only from `sg-lambda`
- [ ] RDS reachable only from `sg-proxy`
- [ ] pgvector extension can be created
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

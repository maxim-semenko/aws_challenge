# INF-09 — IAM authentication to RDS Proxy (stretch)

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | INF — infrastructure as code |
| Milestone | Stretch |
| Role | OPS + BE |
| Size | M |
| Depends on | [BE-03](BE-03.md), [INF-03](INF-03.md) |
| Blocked by | — |
| Unblocks | — |
| Risks watched | — |
| Goals | — |
| References | ADR-006 stage 2 |

## Goal

Remove the database password from the Lambda runtime.

## Scope

**In scope**

- Enable IAM auth on the proxy
- `rds-db:connect` permissions
- Token-based JDBC connection (e.g. AWS Advanced JDBC Wrapper)

**Out of scope**

- Rotation of the master secret (stays in Secrets Manager)

## Plan

- [ ] Enable and grant
- [ ] Switch the datasource
- [ ] Remove secret access from function roles

## Definition of Done

- [ ] Functions connect without a password
- [ ] Secret no longer readable by API functions
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

---
id: T01-03
title: "Week 1 Lambda handlers with the SELECT 1 probe"
phase: P1-environment
status: Blocked
agent: backend
skills: [postgres-pro, test-master]
depends_on: []
blocked_by: [Q-10]
design: ../../design/backend-foundation.md
spec: ../../specs/02-database-connectivity.md
acceptance: [AC-02.5, AC-02.8]
---
# T01-03 — Week 1 Lambda handlers with the SELECT 1 probe

> **BLOCKED** by [Q-10](../../RISKS.md#q-10).

## // BUSINESS CONTEXT

W1-G2 is met only when a function proves the path Lambda → RDS Proxy → PostgreSQL. The handlers are throw-away in
size but not in quality: the probe is the first code that touches credentials, so a leak here is a real incident.

## // TECHNICAL CONSTRAINTS

- Form and location per Q-10 (proposed: plain Java 21, no Spring, separate small Gradle module that builds a zip).
- AWS SDK for Java 2.x for Secrets Manager; PostgreSQL JDBC driver; `sslmode=require`; connect timeout 5 s.
- One connection per invocation, closed in `finally` / try-with-resources; no connection opened during init.
- One JSON log line per invocation with the fields from spec 02; never log the secret, password or a JDBC URL with
  credentials. Errors use the `DB_PROBE_FAILED: <reason>` contract.
- Pre-task invariants from CLAUDE.md: build and unit tests green.

## // SCOPE

**Implement**
- Handlers `admin` (probe), `chatbot`, `sync` (log and return `{"status":"ok"}`)
- Unit tests for the probe logic with the secret client and JDBC connection replaced by test doubles
- Gradle task producing the deployable zip
- Skill file `db-access-from-lambda` (new module, secret read with SDK 2.x, JDBC to the proxy with TLS, logging
  rules; skills ownership rule)

**Exclude**
- Spring, Hikari, SnapStart, Flyway; any change in `backend/`

**Interfaces that must match**
- Input/output and env var names exactly as in [spec 02](../../specs/02-database-connectivity.md) §Inputs/§Outputs.
- Handler class names and zip path are recorded in Notes for T01-04.

## Definition of Done

- [ ] Build and unit tests green on a developer machine
- [ ] No secret value in code, config or logs (AC-02.8 for this code)
- [ ] Skill files added/updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

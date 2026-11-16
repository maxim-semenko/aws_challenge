---
id: T03-07
title: "Admin Lambda deploy and /api routes, access log, throttling, CORS (console runbook)"
phase: P3-rest-api-data
status: Todo
agent: devops
skills: [cloud-architect, http-api-jwt]
depends_on: [T03-01, T03-03, T03-06]
blocked_by: []
design: ../../design/admin-api.md
spec: [../../specs/06-users-table-and-migrations.md, ../../specs/08-admin-api.md]
acceptance: [AC-06.6, AC-08.3, AC-08.4, AC-08.5, AC-08.6, AC-08.7, AC-08.8, AC-08.9]
---
# T03-07 — Admin Lambda deploy and `/api` routes (console runbook)

## // BUSINESS CONTEXT

W3-G2, W3-G3, W3-G5, S4, S8: the endpoints become reachable from the SPA with the contract of CLAUDE.md §6, the
Week 2 routes without a contract disappear, and every request is traceable in CloudWatch.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence without tokens (status codes
  via the browser console snippet pattern of T02-03, adapted to the new paths).
- `aws-challenge-admin`: runtime stays Python 3.12 (ADR-015 revised 2026-11-16; no runtime change), zip from Git (T03-06), timeout 10 s, memory 256 MB, env per spec 06, role
  `rds-db:connect` replaces `secretsmanager:GetSecretValue`; log retention 14 days.
- Routes, permission, access log format, throttling, CORS exactly design admin-api §3 and spec 08; explicit methods
  only (no `ANY`, `OPTIONS`, `$default` — http-api-jwt skill); add new routes before deleting the old ones.
- Tags per CLAUDE.md §7.
- As-built values (proxy resource id, DB user, `DB_NAME`, current `admin` settings and role — facts F1, F3–F5) are
  taken from ENVIRONMENT.md as recorded by T03-03 step 1; if any is missing there, the runbook's first step asks the
  owner to read and report it.

## // SCOPE

**Implement**
- Runbook: admin function update → routes + integration (payload 2.0) → resource-policy check (`SourceArn`) → delete
  `GET /admin`, `POST /chat` → access log → throttling → CORS; verify steps for AC-08.3 … AC-08.9
- ENVIRONMENT.md §HTTP API (routes, log group, throttling, CORS) and §Compute (admin settings); skill `http-api-jwt`
  updated (routes, access log, how to read it)

**Exclude**
- Chat route (Week 5); WAF; custom domain; IaC (T00-03)

**Interfaces that must match**
- Paths, methods and response contract of spec 08; Amplify `VITE_API_URL` unchanged.

## Definition of Done

- [ ] Runbook executed; AC-08.3 … AC-08.9 evidence in Notes
- [ ] ENVIRONMENT.md and skill updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-18. AC-08.5/08.6 need a non-admin and an admin test account
  (T03-01).
- 2026-11-13: Q-18 A accepted by the owner (ADR-006 revised); design admin-api `Accepted` → `Todo` (waits for
  T03-01, T03-03, T03-06 `Done`).

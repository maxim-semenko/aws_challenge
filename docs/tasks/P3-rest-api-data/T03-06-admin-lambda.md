---
id: T03-06
title: "Admin Lambda: GET /api/me and GET /api/admin/users (Python, pytest)"
phase: P3-rest-api-data
status: Todo
agent: backend
skills: [postgres-pro, test-master, http-api-jwt]
depends_on: [T03-02]
blocked_by: []
design: ../../design/admin-api.md
spec: ../../specs/08-admin-api.md
acceptance: [AC-08.1]
---
# T03-06 — Admin Lambda: `GET /api/me` and `GET /api/admin/users`

## // BUSINESS CONTEXT

W3-G2, W3-G3, S3 (curriculum: "Admin Lambda ↔ RDS Proxy"): the administrator's users table needs a paginated,
admin-only endpoint over PostgreSQL; every user needs the own role. The `admin` code moves from the console into Git
(R-15).

## // TECHNICAL CONSTRAINTS

- Conventions of the `python-lambda` skill; shared DB helper; payload format 2.0; claims only from
  `requestContext.authorizer.jwt.claims`.
- Order of checks, responses, errors (problem+json), headers, log line: spec 08 character for character.
- `/api/me` makes no DB call (Q-19 A). Sort column from a fixed whitelist; parameterised SQL; `LIMIT/OFFSET`.
- No secret, token or user data in logs; DB failures → 500 with generic `detail`.
- The Week 1 direct-invoke probe is not kept (design admin-api §2).

## // SCOPE

**Implement**
- `lambdas/admin/` handler, `requirements.txt`, `tests/` covering AC-08.1; zip builds
- Update skill `python-lambda` (API handler section: routing, claims, problem+json, log line)

**Exclude**
- AWS changes (T03-07); SPA (T03-08); filtering by field (not in spec 08); `/api/admin/ping` (dropped)

**Interfaces that must match**
- Endpoint contract: spec 08 §Inputs/§Outputs; table columns: spec 06.

## Definition of Done

- [ ] pytest green (AC-08.1); zip builds
- [ ] Skill updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-18 (DB access) and Q-19 (`/api/me` content).
- 2026-11-13: Q-18 A and Q-19 A accepted by the owner (ADR-006 revised; `/api/me` from claims); design admin-api
  `Accepted` → `Todo` (waits for T03-02 `Done`); scope unchanged.

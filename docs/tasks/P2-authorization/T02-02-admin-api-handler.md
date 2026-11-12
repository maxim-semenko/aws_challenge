---
id: T02-02
title: "Admin Lambda in Git (Python): GET /api/me and GET /api/admin/ping"
phase: P2-authorization
status: Todo
agent: backend
skills: [test-master]
depends_on: [T01-04]
blocked_by: []
design: ../../design/api-gateway-auth.md
spec: ../../specs/05-protected-api.md
acceptance: [AC-05.12]
---
# T02-02 — Admin Lambda in Git (Python): GET /api/me and GET /api/admin/ping

## // BUSINESS CONTEXT

The protected API (W2-G3) and the admin restriction (W2-G4) are served by the Week 1 `admin` function. Its code exists
only in the AWS console today (R-15), so this task first brings it into Git without changing the probe, then adds the
first code that makes an authorisation decision — the `token_use` and group checks must be unit-tested, not assumed.
It is the first Python Lambda task, so it also fixes the repository layout every later function follows.

## // TECHNICAL CONSTRAINTS

- ADR-015: Python 3.13, zip deploy, no backend application. Directory `lambdas/admin/`; the exact layout
  (handler module, `requirements.txt`, tests, how the zip is built on Windows) is decided here and written into the
  skill file.
- Start from the current console code. The agent has no AWS access (CLAUDE.md §3.11): the owner exports the
  deployment package of `aws-challenge-admin` (console: Actions → Export function → Download deployment package) to a
  local path outside the repository and reports the runtime, handler and architecture from the console; record them
  and the probe's dependencies in Notes. Before the code enters the repository, check it for hard-coded secrets or connection strings (CLAUDE.md §7); a finding is
  reported to the owner, not committed.
- The Week 1 probe behaviour for events without `requestContext.http` stays exactly as it is (spec 02 / AC-05.10).
- Routes, claim handling, response fields, problem+json bodies, status codes and `detail` texts exactly as spec 05;
  HTTP API payload format 2.0; JSON field names `camelCase` (CLAUDE.md §6).
- Claims only from `requestContext.authorizer.jwt.claims`; parse `cognito:groups` in both string `[a b]` and JSON
  array form; no database or AWS call on the API routes.
- Log fields per spec 05 §Outputs, one JSON line via the standard library (ADR-012); never log the token, e-mail or
  profile values.
- No new third-party dependency beyond what the probe already uses; tests with `pytest` (ADR-015).
- Do not deploy; the owner uploads the zip in T02-03.

## // SCOPE

**Implement**
- `lambdas/admin/`: the downloaded probe code, route dispatch, `/api/me`, `/api/admin/ping`, problem+json error
  mapping
- pytest unit tests for AC-05.12 (the probe's secret/database access replaced by test doubles)
- Packaging command producing the deployable zip (path recorded in Notes for T02-03)
- Skill file `python-lambda` (layout, handler conventions, payload v2 parsing, claims, `token_use` and group check,
  problem+json, logging, tests, zip packaging; skills ownership rule); CLAUDE.md §9 commands proposed to the owner

**Exclude**
- API Gateway configuration and deployment (T02-03), database access on API routes (Week 3), `chatbot` and `sync`
  code, Powertools (Week 6)

**Interfaces that must match**
- Response JSON exactly as spec 05 §Outputs (consumed by T02-05).
- Handler name and zip path recorded in Notes for T02-03.

## Definition of Done

- [ ] pytest green; AC-05.12 passes; probe behaviour unchanged (test or recorded comparison)
- [ ] No secret in the committed code (checked)
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

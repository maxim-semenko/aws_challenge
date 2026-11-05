# INF-06 — ApiStack: HTTP API with JWT authorizer

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | INF — infrastructure as code |
| Milestone | M1 |
| Role | OPS |
| Size | M |
| Depends on | [INF-04](INF-04.md), [INF-05](INF-05.md) |
| Blocked by | — |
| Unblocks | [OBS-02](OBS-02.md) |
| Risks watched | — |
| Goals | G4, G8 |
| References | ARCHITECTURE.md §3.3, §6, ADR-003 |

## Goal

A single HTTPS entry point that authenticates every call except health.

## Scope

**In scope**

- HTTP API, JWT authorizer (Cognito issuer, client id audience)
- Routes per ARCHITECTURE.md §6 to `chatbot` / `admin` aliases
- `GET /api/health` without auth
- CORS: Amplify domain + `http://localhost:5173`
- Stage access logs in JSON incl. `requestId`
- Stage throttling

**Out of scope**

- Custom domain
- WAF

## Plan

- [ ] Implement the stack
- [ ] Test 401/200 with and without a token
- [ ] Check access log format

## Definition of Done

- [ ] No token → 401
- [ ] `/api/health` → 200
- [ ] Access log lines are JSON with `requestId`
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._

---
id: T02-03
title: "HTTP API with Cognito JWT authorizer, routes, CORS, access logs; deploy admin; first admin"
phase: P2-authorization
status: Todo
agent: devops
skills: [cloud-architect]
depends_on: [T01-04, T02-01, T02-02]
blocked_by: []
design: ../../design/api-gateway-auth.md
spec: [../../specs/05-protected-api.md, ../../specs/04-user-registration-and-sign-in.md]
acceptance: [AC-04.3, AC-05.1, AC-05.2, AC-05.3, AC-05.4, AC-05.5, AC-05.6, AC-05.7, AC-05.8, AC-05.9, AC-05.10, AC-05.11]
---
# T02-03 — HTTP API with Cognito JWT authorizer, routes, CORS, access logs; deploy admin; first admin

## // BUSINESS CONTEXT

The API is the only public door to the functions in the VPC (W2-G3). If the authorizer, the routes or CORS are wrong,
either anyone can call the functions or the SPA cannot call them at all. The first administrator is created here,
without whom the admin route of W2-G4 cannot be proven.

## // TECHNICAL CONSTRAINTS

- AWS CLI commands with profile `awsch`, recorded as a replayable runbook in Notes (Q-12 C).
- API `awsch-dev-api`, HTTP type, settings exactly as in
  [design/api-gateway-auth](../../design/api-gateway-auth.md) §Proposed Solution (authorizer, two routes, no
  `ANY`/`$default` route, payload 2.0, CORS origins, throttling, access log format, retention 14 days).
- Before deploying: invoke `awsch-dev-admin` with `{}` and record the result (baseline for AC-05.10).
- Deploy the T02-02 zip to `awsch-dev-admin`; runtime set to Python 3.13 if the build differs (ADR-015); memory,
  timeout, VPC, role and env vars unchanged.
- Invoke permission for `apigateway.amazonaws.com` with `SourceArn` of this API only.
- Amplify env var `VITE_API_URL` = invoke URL (branch rebuild noted).
- First admin: the owner's account (signed up through the SPA when T02-04 is available, otherwise
  `aws cognito-idp sign-up` + `confirm-sign-up`) added with `admin-add-user-to-group --group-name admin`.
- Tokens used for testing are never written to Notes or logs; evidence shows status codes and decoded claim names only.
- Show every command to the owner and wait for the go-ahead before running it (CLAUDE.md §3.8).

## // SCOPE

**Implement**
- HTTP API, JWT authorizer, routes, integration, stage, CORS, access log group
- Deploy `admin` code; set `VITE_API_URL`; add the owner to `admin`
- Verify AC-04.3, AC-05.1 … AC-05.11 with `curl` and the AWS CLI (test users: the owner = admin, one non-admin test
  user)
- Runbook in Notes; skill file `http-api-jwt` (authorizer settings, ID vs access token audience, CORS, access log
  format, how to add a route; skills ownership rule)

**Exclude**
- `GET /api/health`, custom domain, WAF, IaC code (T00-03)

**Interfaces that must match**
- Paths and methods exactly as spec 05; invoke URL recorded in Notes for T02-05.

## Definition of Done

- [ ] AC-04.3, AC-05.1 … AC-05.11 verified, evidence in Notes
- [ ] Monthly cost noted (per-request only)
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

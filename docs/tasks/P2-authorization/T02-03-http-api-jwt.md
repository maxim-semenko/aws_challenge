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

- No AWS access for the agent (CLAUDE.md §3.11): devops writes a step-by-step console runbook in Notes (page, field,
  exact value); the owner executes it and reports back ids, the invoke URL and screenshots.
- API `aws-challenge-api`, HTTP type, settings exactly as in
  [design/api-gateway-auth](../../design/api-gateway-auth.md) §Proposed Solution (authorizer, two routes, no
  `ANY`/`$default` route, payload 2.0, CORS origins, throttling, access log format, retention 14 days).
- Before the upload: the owner invokes `aws-challenge-admin` with `{}` (console Test tab) and reports the result
  (baseline for AC-05.10).
- The owner uploads the T02-02 zip to `aws-challenge-admin` ("Upload from .zip file"); runtime set to Python 3.13 if
  the build differs (ADR-015); memory, timeout, VPC, role and env vars unchanged.
- Invoke permission for `apigateway.amazonaws.com` with a `SourceArn` of this API only.
- Amplify env var `VITE_API_URL` = invoke URL (branch rebuild noted).
- First admin: the owner's account (signed up through the SPA when T02-04 is available, otherwise created in the
  Cognito console) added to the group `admin` in the Cognito console.
- Tokens used for testing are never written to Notes or logs; evidence shows status codes and decoded claim names only.

## // SCOPE

**Implement**
- Console runbook for: HTTP API, JWT authorizer, routes, integration, stage, CORS, access log group; upload of the
  `admin` zip; `VITE_API_URL`; adding the owner to `admin`
- Verify steps for AC-04.3, AC-05.1 … AC-05.11 (console checks and `curl` commands the owner runs; test users: the
  owner = admin, one non-admin test user); the owner's evidence recorded in Notes
- Skill file `http-api-jwt` (authorizer settings, ID vs access token audience, CORS, access log format, how to add a
  route; skills ownership rule)

**Exclude**
- `GET /api/health`, custom domain, WAF, IaC code (T00-03)

**Interfaces that must match**
- Paths and methods exactly as spec 05; invoke URL recorded in Notes for T02-05.

## Definition of Done

- [ ] Runbook executed by the owner; AC-04.3, AC-05.1 … AC-05.11 verified from the owner's evidence, recorded in Notes
- [ ] Monthly cost noted (per-request only)
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
